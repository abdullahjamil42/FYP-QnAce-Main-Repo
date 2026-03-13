"""
Q&Ace — TTS Engine.

Architecture:
  - Primary: ChatterBox Turbo (350M params, 1-step decoder, low-latency).
  - Fallback: edge-tts (Microsoft Azure free TTS, async, requires internet).
  - Stub: tone generator (always works, for offline testing).

Output: PCM int16 audio at 24 kHz mono.
"""

from __future__ import annotations

import asyncio
import io
import logging
import math
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("qace.tts")

DEFAULT_SAMPLE_RATE = 24_000
DEFAULT_VOICE = "en-US-GuyNeural"  # professional male voice for interviewer persona


# ---------------------------------------------------------------------------
# cuDNN compatibility helper (Windows torch 2.6 + cuDNN 9.1)
# ---------------------------------------------------------------------------

def _cudnn_needs_disable() -> bool:
    """Return True when cuDNN should be disabled during inference.

    torch 2.6.0+cu124 ships cuDNN 9.1 which is missing cudnnGetLibConfig
    (added in 9.2).  Conv1d layers crash with Error 127 if cuDNN is enabled.
    """
    if os.name != "nt":
        return False
    try:
        import ctypes
        dll = ctypes.WinDLL("cudnn64_9.dll")
        return not hasattr(dll, "cudnnGetLibConfig")
    except OSError:
        return False


_CUDNN_DISABLE = None  # lazy-evaluated cache


def _should_disable_cudnn() -> bool:
    global _CUDNN_DISABLE
    if _CUDNN_DISABLE is None:
        _CUDNN_DISABLE = _cudnn_needs_disable()
        if _CUDNN_DISABLE:
            logger.warning("cuDNN 9.1 detected (missing cudnnGetLibConfig) — will disable during TTS inference")
    return _CUDNN_DISABLE


# ---------------------------------------------------------------------------
# ChatterBox Turbo model loader
# ---------------------------------------------------------------------------

def _load_chatterbox_model(device: str = "auto"):
    """Load ChatterBox Turbo TTS model onto GPU (or CPU fallback).

    The library's ``from_pretrained`` forces HF auth (token=True).
    Since ResembleAI/chatterbox-turbo is a public repo we download
    without a token and use ``from_local`` instead.

    cuDNN is temporarily disabled during loading because torch 2.6+cu124
    ships cuDNN 9.1 which crashes with Error 127 (missing cudnnGetLibConfig).
    """
    import torch
    from chatterbox.tts_turbo import ChatterboxTurboTTS

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info("Loading ChatterBox Turbo TTS on %s …", device)
    t0 = time.perf_counter()

    # Disable cuDNN during load to prevent Error 127 on Windows
    # with cuDNN < 9.2 (Conv layers in S3Gen trigger cuDNN init)
    prev_cudnn = torch.backends.cudnn.enabled
    if _should_disable_cudnn():
        torch.backends.cudnn.enabled = False

    try:
        hf_token = os.environ.get("HF_TOKEN")
        if hf_token:
            model = ChatterboxTurboTTS.from_pretrained(device=device)
        else:
            from huggingface_hub import snapshot_download
            local_path = snapshot_download(
                repo_id="ResembleAI/chatterbox-turbo",
                token=False,
                allow_patterns=["*.safetensors", "*.json", "*.txt", "*.pt", "*.model"],
            )
            model = ChatterboxTurboTTS.from_local(local_path, device)
    finally:
        torch.backends.cudnn.enabled = prev_cudnn

    ms = (time.perf_counter() - t0) * 1000.0
    logger.info("ChatterBox Turbo loaded ✓ on %s (%.0fms)", device, ms)
    return model


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------


@dataclass
class TTSResult:
    """Result of synthesizing a single text chunk to PCM audio."""

    audio_pcm: np.ndarray  # int16 mono
    sample_rate: int = DEFAULT_SAMPLE_RATE
    duration_s: float = 0.0
    inference_ms: float = 0.0
    engine_name: str = ""


def _decode_audio_bytes(audio_bytes: bytes, target_sr: int = DEFAULT_SAMPLE_RATE) -> np.ndarray:
    """Decode audio bytes (MP3/WAV/OGG) → PCM int16 using PyAV (FFmpeg)."""
    import av

    container = av.open(io.BytesIO(audio_bytes))
    resampler = av.audio.resampler.AudioResampler(
        format="s16",
        layout="mono",
        rate=target_sr,
    )
    frames: list[np.ndarray] = []
    for frame in container.decode(audio=0):
        for rf in resampler.resample(frame):
            frames.append(rf.to_ndarray().flatten())
    container.close()

    if not frames:
        return np.zeros(target_sr, dtype=np.int16)
    return np.concatenate(frames).astype(np.int16)


async def _synthesize_edge(text: str, voice: str, rate: str = "+0%") -> TTSResult:
    """Synthesize via edge-tts (free Microsoft Azure TTS)."""
    import edge_tts

    t0 = time.perf_counter()
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]

    if not audio_bytes:
        logger.warning("edge-tts returned empty audio for: %s", text[:40])
        return _synthesize_tone(text)

    pcm = _decode_audio_bytes(audio_bytes, DEFAULT_SAMPLE_RATE)
    dur = len(pcm) / DEFAULT_SAMPLE_RATE
    ms = (time.perf_counter() - t0) * 1000.0
    logger.info("edge-tts: %.1fs audio in %.0fms (%d chars)", dur, ms, len(text))
    return TTSResult(pcm, DEFAULT_SAMPLE_RATE, dur, ms, "edge-tts")


def _synthesize_tone(text: str, freq: float = 330.0) -> TTSResult:
    """Fallback: generate a gentle tone whose duration matches speaking pace."""
    words = max(len(text.split()), 1)
    dur = min(words * 0.15, 10.0)
    n = int(dur * DEFAULT_SAMPLE_RATE)
    t = np.linspace(0, dur, n, endpoint=False)
    env = np.minimum(t / 0.05, 1.0) * np.minimum((dur - t) / 0.05, 1.0)
    wave = (np.sin(2 * math.pi * freq * t) * env * 6000).astype(np.int16)
    return TTSResult(wave, DEFAULT_SAMPLE_RATE, dur, 0.1, "tone-generator")


def _synthesize_silence(duration_s: float = 0.3) -> TTSResult:
    n = int(duration_s * DEFAULT_SAMPLE_RATE)
    return TTSResult(np.zeros(n, dtype=np.int16), DEFAULT_SAMPLE_RATE, duration_s, 0.0, "silence")


def _float_audio_to_pcm_int16(audio: np.ndarray) -> np.ndarray:
    audio = np.asarray(audio)
    if audio.ndim > 1:
        audio = audio.reshape(-1)
    if audio.dtype == np.int16:
        return audio
    audio = np.clip(audio.astype(np.float32), -1.0, 1.0)
    return (audio * 32767.0).astype(np.int16)


# ---------------------------------------------------------------------------
# Engine class
# ---------------------------------------------------------------------------


class TTSEngine:
    """
    TTS engine manager.

    Priority:
      1. ChatterBox Turbo (local GPU, 350M params, low-latency)
      2. edge-tts (Microsoft Azure, async, internet required)
      3. Tone generator (always works)
    """

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        backend: str = "auto",
        chatterbox_device: str = "auto",
    ):
        self.voice = voice
        self.backend = (backend or "auto").strip().lower()
        self.chatterbox_model: Any = None
        self.chatterbox_device = chatterbox_device
        self._cb_lock = asyncio.Lock()
        self._engine_name = self._detect_engine()

    def _disable_chatterbox(self, reason: str) -> None:
        if self._engine_name != "chatterbox-turbo":
            return
        self.chatterbox_model = None
        try:
            import edge_tts  # noqa: F401
            self._engine_name = "edge-tts"
        except ImportError:
            self._engine_name = "tone-generator"
        logger.warning(
            "Disabling ChatterBox TTS (%s) — switching to %s", reason, self._engine_name
        )

    def _detect_engine(self) -> str:
        # If explicitly set to edge, skip ChatterBox
        if self.backend == "edge":
            try:
                import edge_tts  # noqa: F401
                logger.info("TTS engine: edge-tts (Microsoft Azure) [explicit]")
                return "edge-tts"
            except ImportError:
                logger.warning("edge-tts requested but not installed — falling back to tone")
                return "tone-generator"

        if self.backend in ("chatterbox", "auto"):
            try:
                self.chatterbox_model = _load_chatterbox_model(self.chatterbox_device)
                logger.info("TTS engine: ChatterBox Turbo (local GPU)")
                return "chatterbox-turbo"
            except Exception as exc:
                logger.warning("ChatterBox Turbo load failed (%s) — falling back", exc)

        if self.backend == "chatterbox":
            logger.warning("ChatterBox requested but unavailable — using fallback backend")

        try:
            import edge_tts  # noqa: F401
            logger.info("TTS engine: edge-tts (Microsoft Azure)")
            return "edge-tts"
        except ImportError:
            logger.info("TTS engine: tone generator (fallback)")
            return "tone-generator"

    @property
    def engine_name(self) -> str:
        return self._engine_name

    async def synthesize(self, text: str) -> TTSResult:
        """Synthesize *text* to PCM int16 audio."""
        if not text or not text.strip():
            return _synthesize_silence(0.2)

        if self._engine_name == "chatterbox-turbo":
            return await self._synthesize_chatterbox(text)
        if self._engine_name == "edge-tts":
            try:
                return await _synthesize_edge(text, self.voice)
            except Exception as exc:
                logger.warning("edge-tts failed (%s) — falling back to tone", exc)
                return _synthesize_tone(text)
        return _synthesize_tone(text)

    async def _synthesize_chatterbox(self, text: str) -> TTSResult:
        """Synthesize with ChatterBox Turbo TTS."""
        async with self._cb_lock:
            if self.chatterbox_model is None:
                logger.warning("ChatterBox TTS requested without a loaded model — falling back")
                try:
                    return await _synthesize_edge(text, self.voice)
                except Exception:
                    return _synthesize_tone(text)

            disable_cudnn = _should_disable_cudnn()

            def _run_chatterbox() -> tuple[np.ndarray, int]:
                import torch

                prev_cudnn = torch.backends.cudnn.enabled
                if disable_cudnn:
                    torch.backends.cudnn.enabled = False
                try:
                    wav = self.chatterbox_model.generate(text)
                    sr = self.chatterbox_model.sr
                    # wav is a torch tensor [1, samples] or [samples]
                    if hasattr(wav, "cpu"):
                        wav = wav.cpu().numpy()
                    wav = np.asarray(wav).squeeze()
                    return _float_audio_to_pcm_int16(wav), int(sr)
                finally:
                    torch.backends.cudnn.enabled = prev_cudnn

            TTS_TIMEOUT_S = 30.0
            t0 = time.perf_counter()
            try:
                loop = asyncio.get_running_loop()
                pcm, sr = await asyncio.wait_for(
                    loop.run_in_executor(None, _run_chatterbox),
                    timeout=TTS_TIMEOUT_S,
                )
                dur = len(pcm) / max(sr, 1)
                ms = (time.perf_counter() - t0) * 1000.0
                logger.info("chatterbox-turbo: %.1fs audio in %.0fms (%d chars)", dur, ms, len(text))
                return TTSResult(pcm, sr, dur, ms, "chatterbox-turbo")
            except asyncio.TimeoutError:
                ms = (time.perf_counter() - t0) * 1000.0
                logger.warning("ChatterBox TTS timed out after %.0fms — falling back", ms)
                self._disable_chatterbox(f"timeout after {ms:.0f}ms")
                try:
                    return await _synthesize_edge(text, self.voice)
                except Exception:
                    return _synthesize_tone(text)
            except Exception as exc:
                logger.warning("ChatterBox TTS synth failed (%s) — falling back", exc)
                self._disable_chatterbox(str(exc))
                try:
                    return await _synthesize_edge(text, self.voice)
                except Exception:
                    return _synthesize_tone(text)


def create_tts_engine(
    voice: str = DEFAULT_VOICE,
    backend: str = "auto",
    chatterbox_device: str = "auto",
) -> TTSEngine:
    """Factory — creates a TTS engine with the best available backend."""
    return TTSEngine(
        voice=voice,
        backend=backend,
        chatterbox_device=chatterbox_device,
    )
