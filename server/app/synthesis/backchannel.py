"""
Q&Ace — Backchannel Audio System.

Provides:
  - ``BackchannelTrack`` — a silent WebRTC audio track that can play
    short phrases ("mhm", "right") on demand.
  - ``BackchannelManager`` — trigger logic that decides when to fire
    a backchannel based on VAD speech-end events, cooldown, randomness,
    and interview phase.
"""

from __future__ import annotations

import asyncio
import fractions
import logging
import random
import time
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("qace.backchannel")

# ── Phrase pool ──────────────────────────────────────────────────────────
BACKCHANNEL_PHRASES = ["Mhm.", "Right.", "Okay.", "I see.", "Sure.", "Mm."]

# ── Audio constants ──────────────────────────────────────────────────────
_OUTPUT_RATE = 48_000
_FRAME_SAMPLES = 960   # 20ms at 48kHz
_VOLUME_SCALE = 0.85   # 85% volume for backchannels
_COOLDOWN_S = 8.0      # minimum seconds between backchannels
_DELAY_S = 0.6         # delay after VAD speech-end before checking
_MIN_PAUSE_S = 0.8     # minimum total silence to trigger
_MAX_PAUSE_S = 2.5     # maximum silence — too long means they stopped
_MIN_ANSWER_AGE_S = 6.0  # don't backchannel in the first 6s of answering
_TRIGGER_PROB = 0.35   # probability of firing when all conditions pass


# ── BackchannelTrack ─────────────────────────────────────────────────────

def _get_base_class():
    """Return aiortc.MediaStreamTrack or a no-op stub."""
    try:
        from aiortc import MediaStreamTrack
        return MediaStreamTrack
    except ImportError:
        class _Stub:
            kind = ""
            def __init__(self): pass
            async def recv(self): pass
        return _Stub


class BackchannelTrack(_get_base_class()):
    """
    A WebRTC audio track dedicated to backchannel playback.

    Emits 20ms silence frames when idle. When ``play()`` is called
    with PCM audio, enqueues it for immediate playback. ``cancel()``
    flushes the queue (for speech-resumption cutoff).
    """

    kind = "audio"

    def __init__(self):
        super().__init__()
        self._queue: asyncio.Queue[np.ndarray] = asyncio.Queue()
        self._pts = 0
        self._time_base = fractions.Fraction(1, 90_000)
        self._start: Optional[float] = None
        self._cancelled = False
        self._playing = False

    @property
    def is_playing(self) -> bool:
        return self._playing and not self._queue.empty()

    def play(self, audio_pcm: np.ndarray, sample_rate: int = 24_000) -> None:
        """Enqueue PCM audio for playback. Resamples to 48kHz if needed."""
        self._cancelled = False
        self._playing = True

        # Resample if needed
        if sample_rate != _OUTPUT_RATE:
            ratio = _OUTPUT_RATE / sample_rate
            new_len = int(len(audio_pcm) * ratio)
            indices = np.linspace(0, len(audio_pcm) - 1, new_len).astype(int)
            audio_pcm = audio_pcm[indices]

        # Scale volume
        audio_pcm = (audio_pcm.astype(np.float32) * _VOLUME_SCALE).astype(np.int16)

        # Split into 20ms frames
        for i in range(0, len(audio_pcm) - _FRAME_SAMPLES + 1, _FRAME_SAMPLES):
            self._queue.put_nowait(audio_pcm[i: i + _FRAME_SAMPLES])

    def cancel(self) -> None:
        """Flush playback queue immediately (speech resumed)."""
        self._cancelled = True
        self._playing = False
        # Drain the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def recv(self):
        """Produce the next 20ms audio frame."""
        try:
            from av import AudioFrame
        except ImportError:
            await asyncio.sleep(0.02)
            return None

        if self._start is None:
            self._start = time.time()

        # Try to get a queued frame (non-blocking)
        try:
            samples = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            samples = np.zeros(_FRAME_SAMPLES, dtype=np.int16)
            if self._playing:
                self._playing = False

        frame = AudioFrame(format="s16", layout="mono", samples=_FRAME_SAMPLES)
        frame.sample_rate = _OUTPUT_RATE
        frame.pts = self._pts
        frame.time_base = self._time_base
        frame.planes[0].update(samples.tobytes())

        self._pts += _FRAME_SAMPLES

        # Pace to ~20ms per frame
        target_time = self._start + (self._pts / _OUTPUT_RATE)
        wait = target_time - time.time()
        if wait > 0:
            await asyncio.sleep(wait)

        return frame


# ── BackchannelManager ───────────────────────────────────────────────────

class BackchannelManager:
    """
    Decides when to play backchannel audio based on VAD events.

    Call ``on_speech_end()`` whenever the VAD fires a speech-end event
    (~200ms after silence onset). The manager schedules a delayed check
    and, if conditions are met, synthesizes and plays a short phrase.
    """

    def __init__(
        self,
        session: dict[str, Any],
        tts_engine: Any,
        backchannel_track: BackchannelTrack,
    ):
        self._session = session
        self._tts = tts_engine
        self._track = backchannel_track
        self._pending_handle: Optional[asyncio.TimerHandle] = None
        self._speech_end_time: Optional[float] = None

    def on_speech_end(self) -> None:
        """Called when VAD fires on_speech_end."""
        self._speech_end_time = time.perf_counter()

        # Cancel any pending check
        if self._pending_handle is not None:
            self._pending_handle.cancel()

        # Schedule delayed check
        loop = asyncio.get_event_loop()
        self._pending_handle = loop.call_later(
            _DELAY_S,
            lambda: asyncio.ensure_future(self._delayed_check()),
        )

    def on_speech_start(self) -> None:
        """Called when VAD detects speech resumption — cancel pending + cut playback."""
        # Cancel pending check
        if self._pending_handle is not None:
            self._pending_handle.cancel()
            self._pending_handle = None

        # Cut active backchannel playback
        if self._session.get("backchannel_active"):
            self._track.cancel()
            self._session["backchannel_active"] = False
            # Log as cut short
            bc_log = self._session.get("backchannel_log", [])
            if bc_log and not bc_log[-1].get("cut_short"):
                bc_log[-1]["cut_short"] = True
            logger.debug("Backchannel cut short by speech resumption")

    async def _delayed_check(self) -> None:
        """Check trigger conditions ~0.8s after speech end."""
        self._pending_handle = None

        if self._speech_end_time is None:
            return

        silence_elapsed = time.perf_counter() - self._speech_end_time

        # 1. Silence between 0.8s and 2.5s
        if silence_elapsed < _MIN_PAUSE_S or silence_elapsed > _MAX_PAUSE_S:
            return

        # 2. Must be in answering phase
        if self._session.get("current_phase") != "answering":
            return

        # 3. At least 6s into the answer (not during opening breath)
        prompted_at = self._session.get("answer_prompted_at")
        if prompted_at and (time.perf_counter() - prompted_at) < _MIN_ANSWER_AGE_S:
            return

        # 4. Cooldown — at least 8s since last backchannel
        last_bc = self._session.get("last_backchannel_time")
        if last_bc and (time.perf_counter() - last_bc) < _COOLDOWN_S:
            return

        # 5. Randomness gate
        if random.random() >= _TRIGGER_PROB:
            return

        # 6. Not already playing
        if self._session.get("backchannel_active"):
            return

        # All conditions met — synthesize and play
        await self._fire_backchannel()

    async def _fire_backchannel(self) -> None:
        """Synthesize a random backchannel phrase and play it."""
        phrase = random.choice(BACKCHANNEL_PHRASES)

        if self._tts is None:
            logger.debug("No TTS engine — skipping backchannel")
            return

        try:
            self._session["backchannel_active"] = True
            result = await self._tts.synthesize(phrase)

            if result.audio_pcm is None or len(result.audio_pcm) == 0:
                self._session["backchannel_active"] = False
                return

            self._track.play(result.audio_pcm, result.sample_rate)

            # Log it
            bc_log = self._session.get("backchannel_log", [])
            bc_log.append({
                "timestamp": time.perf_counter(),
                "phrase": phrase,
                "cut_short": False,
            })
            self._session["backchannel_log"] = bc_log
            self._session["last_backchannel_time"] = time.perf_counter()

            logger.info("Backchannel fired: '%s'", phrase)

            # Wait for playback to finish (non-blocking — we just mark inactive)
            duration_s = len(result.audio_pcm) / result.sample_rate
            await asyncio.sleep(duration_s)

            if self._session.get("backchannel_active"):
                self._session["backchannel_active"] = False

        except Exception as exc:
            logger.warning("Backchannel synthesis failed: %s", exc)
            self._session["backchannel_active"] = False
