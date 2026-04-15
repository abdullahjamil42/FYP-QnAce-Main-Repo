"""
Q&Ace — WebRTC track handlers (inbound + outbound).

Inbound:
  - consume_audio_track: client mic → resample 48→16 kHz mono → VAD / ring buffer.

Outbound (Phase 4):
  - TTSAudioStreamTrack:   TTS PCM  → Opus frames streamed to client.
  - AvatarVideoStreamTrack: Avatar RGB → VP8 frames streamed to client.
"""

from __future__ import annotations

import asyncio
import fractions
import logging
import time
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("qace.tracks")

TARGET_RATE = 16_000  # 16 kHz for Whisper / VAD


def resample_linear(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Fast linear interpolation resampler (no scipy required)."""
    if src_rate == dst_rate:
        return audio
    ratio = dst_rate / src_rate
    n_out = int(len(audio) * ratio)
    indices = np.linspace(0, len(audio) - 1, n_out)
    idx_floor = np.floor(indices).astype(np.int64)
    idx_ceil = np.minimum(idx_floor + 1, len(audio) - 1)
    frac = indices - idx_floor
    out = audio[idx_floor] * (1.0 - frac) + audio[idx_ceil] * frac
    return out.astype(audio.dtype)


def to_mono_int16(frame_data: np.ndarray, channels: int) -> np.ndarray:
    """Convert multi-channel audio to mono int16."""
    if frame_data.dtype != np.int16:
        frame_data = frame_data.astype(np.int16)
    if channels > 1 and len(frame_data) >= channels:
        # Reshape to (samples, channels) and mean across channels
        n_samples = len(frame_data) // channels
        frame_data = frame_data[: n_samples * channels].reshape(n_samples, channels)
        frame_data = frame_data.mean(axis=1).astype(np.int16)
    return frame_data


async def consume_audio_track(
    track: Any,
    ring_buffer: Any,
    eos_detector: Any,
    session: dict,
) -> None:
    """
    Consume frames from an aiortc AudioStreamTrack.

    - Resamples to 16 kHz mono int16.
    - Writes to ring buffer.
    - Feeds the VAD end-of-speech detector.

    ``session`` dict is used to look up the current data_channel dynamically
    (it may not be open yet when the track handler fires).
    """
    from ..webrtc.data_channel import send_status

    def _dc():
        return session.get("data_channel")

    send_status(_dc(), "audio-track-received")
    logger.info("Audio track consumer started")

    frame_count = 0
    last_log = time.time()
    last_rms_log = time.time()

    try:
        while True:
            try:
                frame = await asyncio.wait_for(track.recv(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Audio frame timeout (5s) — flushing VAD")
                send_status(_dc(), "audio-frame-timeout")
                if eos_detector:
                    eos_detector.flush()
                continue
            except Exception as exc:
                # Track ended or error
                logger.info("Audio track ended: %s", exc)
                break

            # Extract raw samples from aiortc AudioFrame
            try:
                raw = frame.to_ndarray()
                src_rate = frame.sample_rate
                channels = len(frame.layout.channels) if hasattr(frame, "layout") else 1
            except Exception:
                # Fallback: try raw planes
                try:
                    raw = np.frombuffer(bytes(frame.planes[0]), dtype=np.int16)
                    src_rate = 48000
                    channels = 1
                except Exception:
                    continue

            # Convert: multi-channel → mono → resample → int16
            mono = to_mono_int16(raw.flatten(), channels)
            if src_rate != TARGET_RATE:
                mono = resample_linear(mono.astype(np.float32), src_rate, TARGET_RATE).astype(
                    np.int16
                )

            # Feed into ring buffer and VAD
            if ring_buffer:
                ring_buffer.write(mono)
            if eos_detector:
                eos_detector.feed(mono)

            frame_count += 1
            now = time.time()
            if now - last_log > 10.0:
                logger.debug("Audio frames received: %d", frame_count)
                last_log = now

            # Periodic RMS + VAD diagnostic (every 3s)
            if now - last_rms_log > 3.0:
                import numpy as _np
                rms = float(_np.sqrt(_np.mean(mono.astype(_np.float32) ** 2)))
                speaking = eos_detector.is_speaking if eos_detector else False
                msg = f"audio rms={rms:.0f} speaking={speaking} frames={frame_count}"
                logger.info(msg)
                send_status(_dc(), msg)
                last_rms_log = now

    except asyncio.CancelledError:
        logger.info("Audio consumer cancelled")
    finally:
        # Flush any remaining speech
        if eos_detector:
            eos_detector.flush()
        send_status(_dc(), "audio-consumer-stopped")
        logger.info("Audio track consumer stopped (total frames: %d)", frame_count)


# ── Lazy aiortc import (only when WebRTC runtime is present) ──

def _get_media_stream_track_base():
    """Return aiortc.MediaStreamTrack or a no-op base for testing."""
    try:
        from aiortc import MediaStreamTrack
        return MediaStreamTrack
    except ImportError:
        # Minimal stub so the classes can be defined even without aiortc
        class _Stub:
            kind = ""
            def __init__(self): pass
            async def recv(self): ...
        return _Stub


# ---------------------------------------------------------------------------
# Outbound: TTS audio → Opus
# ---------------------------------------------------------------------------


class TTSAudioStreamTrack(_get_media_stream_track_base()):
    """Stream TTS PCM audio back to the browser via WebRTC audio track."""

    kind = "audio"

    def __init__(self, output_rate: int = 48_000):
        super().__init__()
        self._output_rate = output_rate
        self._frame_duration = 0.020  # 20 ms Opus frames
        self._samples_per_frame = int(output_rate * self._frame_duration)
        self._queue: asyncio.Queue[Optional[np.ndarray]] = asyncio.Queue()
        self._buffer = np.array([], dtype=np.int16)
        self._pts = 0
        self._start: Optional[float] = None
        self._finished = False

    # -- public API --

    def enqueue_audio(self, pcm_int16: np.ndarray, sample_rate: int = 24_000) -> None:
        """Push a PCM chunk (any sample rate) into the playback queue."""
        if sample_rate != self._output_rate:
            pcm_int16 = resample_linear(
                pcm_int16.astype(np.float32), sample_rate, self._output_rate
            ).astype(np.int16)
        self._queue.put_nowait(pcm_int16)

    def finish(self) -> None:
        """Signal end of current TTS utterance (track continues with silence)."""
        self._queue.put_nowait(None)

    def is_queue_drained(self) -> bool:
        """Return True if the playback queue and buffer are both empty."""
        return self._queue.empty() and len(self._buffer) == 0

    async def wait_until_drained(self, poll_interval: float = 0.1, timeout: float = 30.0) -> bool:
        """Wait until the track has fully drained into the WebRTC stream."""
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if self.is_queue_drained():
                return True
            await asyncio.sleep(poll_interval)
        return False  # timed out

    # -- aiortc recv --

    async def recv(self):  # noqa: D401
        import av

        if self._start is None:
            self._start = time.time()

        # pace output to real-time
        expected = self._start + (self._pts / self._output_rate)
        delay = expected - time.time()
        if delay > 0:
            await asyncio.sleep(delay)

        # drain queue into buffer
        while len(self._buffer) < self._samples_per_frame:
            try:
                chunk = self._queue.get_nowait()
                if chunk is None:
                    self._finished = False  # allow re-use for next utterance
                    break
                self._buffer = np.concatenate([self._buffer, chunk])
            except asyncio.QueueEmpty:
                break

        # extract one frame (pad with silence if needed)
        if len(self._buffer) >= self._samples_per_frame:
            data = self._buffer[: self._samples_per_frame]
            self._buffer = self._buffer[self._samples_per_frame :]
        else:
            data = np.zeros(self._samples_per_frame, dtype=np.int16)
            if len(self._buffer) > 0:
                data[: len(self._buffer)] = self._buffer
                self._buffer = np.array([], dtype=np.int16)

        frame = av.AudioFrame.from_ndarray(
            data.reshape(1, -1), format="s16", layout="mono"
        )
        frame.sample_rate = self._output_rate
        frame.pts = self._pts
        frame.time_base = fractions.Fraction(1, self._output_rate)
        self._pts += self._samples_per_frame
        return frame


# ---------------------------------------------------------------------------
# Outbound: Avatar video → VP8
# ---------------------------------------------------------------------------


class AvatarVideoStreamTrack(_get_media_stream_track_base()):
    """Stream rendered avatar frames to the browser @ TARGET_FPS."""

    kind = "video"

    def __init__(
        self,
        avatar_engine: Any = None,
        session: Optional[dict] = None,
        fps: int = 30,
        width: int = 512,
        height: int = 512,
    ):
        super().__init__()
        self._avatar_engine = avatar_engine
        self._session = session or {}
        self._fps = fps
        self._width = width
        self._height = height
        self._pts = 0
        self._time_base = fractions.Fraction(1, 90_000)
        self._start: Optional[float] = None

    async def recv(self):  # noqa: D401
        import av

        if self._start is None:
            self._start = time.time()

        pts_time = self._pts / 90_000.0
        expected = self._start + pts_time
        delay = expected - time.time()
        if delay > 0:
            await asyncio.sleep(delay)

        # render one frame
        if self._avatar_engine is not None:
            is_speaking = self._session.get("speaking", False)
            energy = self._session.get("audio_energy", 0.0)
            avatar_frame = self._avatar_engine.render_frame(
                audio_energy=energy, is_speaking=is_speaking
            )
            rgb = avatar_frame.frame_rgb
        else:
            rgb = np.zeros((self._height, self._width, 3), dtype=np.uint8)

        frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
        frame.pts = self._pts
        frame.time_base = self._time_base
        self._pts += int(90_000 / self._fps)
        return frame

