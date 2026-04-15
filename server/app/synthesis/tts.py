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
import re
import time
import site
import glob
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
try:
    import librosa
except ImportError:
    librosa = None

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
    force_enable = os.environ.get("QACE_FORCE_ENABLE_CUDNN", "").strip().lower()
    if force_enable in {"1", "true", "yes", "on"}:
        return False

    force = os.environ.get("QACE_FORCE_DISABLE_CUDNN", "").strip().lower()
    if force in {"1", "true", "yes", "on"}:
        return True

    if os.name != "nt":
        return False
    try:
        import ctypes

        # Prefer cuDNN wheels in the current Python env on Windows.
        roots = site.getsitepackages() + [site.getusersitepackages()]
        bins: list[str] = []
        patterns = [
            ("nvidia", "cudnn", "bin"),
            ("nvidia", "cublas", "bin"),
            ("nvidia", "cuda_nvrtc", "bin"),
            ("nvidia", "cuda_runtime", "bin"),
        ]
        for root in roots:
            for pat in patterns:
                bins.extend(glob.glob(os.path.join(root, *pat)))
        bins = [p for p in bins if os.path.isdir(p)]
        for p in bins:
            try:
                os.add_dll_directory(p)
            except Exception:
                pass

        candidates: list[str] = []
        for p in bins:
            candidates.extend(glob.glob(os.path.join(p, "cudnn64_9.dll")))
        cudnn_bin = os.path.dirname(candidates[0]) if candidates else ""

        # Some Windows setups require explicit preload of split cuDNN DLLs.
        preload = [
            "cudnn_ops64_9.dll",
            "cudnn_cnn64_9.dll",
            "cudnn_adv64_9.dll",
            "cudnn_graph64_9.dll",
            "cudnn_heuristic64_9.dll",
            "cudnn_engines_precompiled64_9.dll",
            "cudnn_engines_runtime_compiled64_9.dll",
        ]
        if cudnn_bin:
            for name in preload:
                try:
                    ctypes.WinDLL(os.path.join(cudnn_bin, name))
                except Exception:
                    pass

        dll_path = candidates[0] if candidates else "cudnn64_9.dll"
        dll = ctypes.WinDLL(dll_path)

        # Primary signal: runtime cuDNN version.
        try:
            dll.cudnnGetVersion.restype = ctypes.c_size_t
            ver = int(dll.cudnnGetVersion())
            # cuDNN 9.2.x => 902xx. Disable only for versions below 9.2.
            return ver < 90200
        except Exception:
            # Fallback signal for older builds.
            return not hasattr(dll, "cudnnGetLibConfig")
    except OSError:
        return False


_CUDNN_DISABLE = None  # lazy-evaluated cache


def _should_disable_cudnn() -> bool:
    global _CUDNN_DISABLE
    if _CUDNN_DISABLE is None:
        _CUDNN_DISABLE = _cudnn_needs_disable()
        if _CUDNN_DISABLE:
            logger.warning("cuDNN runtime detected as < 9.2 (or incompatible) — will disable during TTS inference")
    return _CUDNN_DISABLE


def split_text_for_tts_streaming(text: str, max_chars: int = 150) -> list[str]:
    """Split text into sentence-like chunks capped by max_chars for faster synth."""
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    if not normalized:
        return []

    # Primary split by sentence boundaries.
    sentence_parts = [
        p.strip() for p in re.split(r"(?<=[.!?])\s+", normalized) if p.strip()
    ]
    if not sentence_parts:
        sentence_parts = [normalized]

    chunks: list[str] = []
    cap = max(40, int(max_chars))
    for part in sentence_parts:
        if len(part) <= cap:
            chunks.append(part)
            continue

        # Secondary split by comma/semicolon for long sentences.
        clauses = [c.strip() for c in re.split(r"(?<=[,;:])\s+", part) if c.strip()]
        if not clauses:
            clauses = [part]

        current = ""
        for clause in clauses:
            if not current:
                current = clause
                continue
            candidate = f"{current} {clause}"
            if len(candidate) <= cap:
                current = candidate
            else:
                chunks.append(current)
                current = clause
        if current:
            chunks.append(current)

    # Final safety: hard wrap anything still over cap by whitespace.
    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= cap:
            final_chunks.append(chunk)
            continue
        words = chunk.split()
        current = ""
        for w in words:
            candidate = w if not current else f"{current} {w}"
            if len(candidate) <= cap:
                current = candidate
            else:
                if current:
                    final_chunks.append(current)
                current = w
        if current:
            final_chunks.append(current)

    return final_chunks


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

    if device == "cuda":
        # Enable SDPA for optimized attention kernels
        torch.backends.cuda.enable_flash_sdp(True)
        torch.backends.cuda.enable_mem_efficient_sdp(True)
        torch.backends.cuda.enable_math_sdp(False)
        logger.info("SDPA Kernels enabled: Flash=%s, MemEfficient=%s", 
                    torch.backends.cuda.flash_sdp_enabled(),
                    torch.backends.cuda.mem_efficient_sdp_enabled())

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
        
        if device == "cuda":
            # Problem 2 Fix: Force FP16 and move to device properly
            try:
                target = getattr(model, "model", model)
                if hasattr(target, "half"):
                    target = target.half()
                if hasattr(target, "to"):
                    target = target.to(device)
                
                if hasattr(model, "model"):
                    model.model = target
                else:
                    model = target
                
                # Verify dtype
                param_dtype = next(target.parameters()).dtype if hasattr(target, "parameters") else "unknown"
                logger.info("ChatterBox model cast to half precision ✓ (dtype: %s)", param_dtype)
            except Exception as e:
                logger.warning("Could not cast ChatterBox model to half precision: %s", e)
    finally:
        torch.backends.cudnn.enabled = prev_cudnn

    # FP16 is already applied above via model.half().to(device).
    # Skip the duplicate env-var-gated half() — double-casting can corrupt state.

    # torch.compile: disabled by default on Windows (known to crash with
    # reduce-overhead mode).  Set QACE_CHATTERBOX_COMPILE=1 to force-enable.
    if device == "cuda":
        default_compile = "0" if os.name == "nt" else "1"
        use_compile = os.environ.get("QACE_CHATTERBOX_COMPILE", default_compile).strip().lower() in {
            "1", "true", "yes", "on"
        }
        if use_compile and hasattr(torch, "compile"):
            target_module = None
            try:
                import torch.nn as nn
                if isinstance(getattr(model, "model", None), nn.Module):
                    target_module = model.model
                elif isinstance(model, nn.Module):
                    target_module = model
            except Exception:
                target_module = None

            if target_module is not None:
                try:
                    compiled = torch.compile(target_module, mode="reduce-overhead")
                    if getattr(model, "model", None) is target_module:
                        model.model = compiled
                    else:
                        model = compiled
                    logger.info("ChatterBox runtime: torch.compile enabled (reduce-overhead)")
                except Exception as exc:
                    logger.warning("ChatterBox compile failed (%s) — continuing without compile", exc)
        else:
            logger.info("ChatterBox runtime: torch.compile skipped (os=%s, env=%s)", os.name, default_compile)

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

    # Normalize channel layouts into a single mono stream.
    if audio.ndim == 2:
        # Common layouts: [channels, samples] or [samples, channels]
        if audio.shape[0] <= 4:
            audio = audio.mean(axis=0)
        elif audio.shape[1] <= 4:
            audio = audio.mean(axis=1)
        else:
            audio = audio.reshape(-1)
    elif audio.ndim > 2:
        audio = audio.reshape(-1)

    if audio.dtype == np.int16:
        return audio

    audio = audio.astype(np.float32)
    # Guard against model-instability artifacts (NaN/Inf) that become static.
    audio = np.nan_to_num(audio, nan=0.0, posinf=1.0, neginf=-1.0)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1.0:
        audio = audio / peak

    audio = np.clip(audio, -1.0, 1.0)
    return (audio * 32767.0).astype(np.int16)

def time_stretch_audio(pcm: np.ndarray, sample_rate: int, rate: float) -> np.ndarray:
    if rate == 1.0 or len(pcm) == 0:
        return pcm
    try:
        if librosa is None:
            logger.warning("librosa not installed, skipping time_stretch")
            return pcm
        audio_f32 = pcm.astype(np.float32) / 32768.0
        stretched = librosa.effects.time_stretch(y=audio_f32, rate=rate)
        return _float_audio_to_pcm_int16(stretched)
    except Exception as e:
        logger.warning("time_stretch_audio failed: %s", e)
        return pcm

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
        self._cb_fail_count = 0  # 3-strike counter for ChatterBox failures
        self._CB_MAX_FAILURES = 3
        self._engine_name = self._detect_engine()

    def _disable_chatterbox(self, reason: str) -> None:
        """Track ChatterBox failures. Only permanently disable after 3 consecutive failures."""
        if self._engine_name != "chatterbox-turbo":
            return
        self._cb_fail_count += 1
        if self._cb_fail_count < self._CB_MAX_FAILURES:
            logger.warning(
                "ChatterBox TTS failed (%s) — strike %d/%d, will retry next call",
                reason, self._cb_fail_count, self._CB_MAX_FAILURES,
            )
            return
        # Permanent disable after 3 strikes
        self.chatterbox_model = None
        try:
            import edge_tts  # noqa: F401
            self._engine_name = "edge-tts"
        except ImportError:
            self._engine_name = "tone-generator"
        logger.error(
            "Permanently disabling ChatterBox TTS after %d failures (%s) — switching to %s",
            self._cb_fail_count, reason, self._engine_name,
        )

    def _reset_cb_fail_count(self) -> None:
        """Reset failure counter on successful synthesis."""
        if self._cb_fail_count > 0:
            self._cb_fail_count = 0

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

    async def synthesize(self, text: str, stress_level: str = "none") -> TTSResult:
        """Synthesize *text* to PCM int16 audio."""
        if not text or not text.strip():
            return _synthesize_silence(0.2)

        rate = 1.0
        if stress_level == "brutal":
            rate = 1.22
        elif stress_level == "high":
            rate = 1.12

        res = None
        if self._engine_name == "chatterbox-turbo":
            res = await self._synthesize_chatterbox(text)
        elif self._engine_name == "edge-tts":
            try:
                # edge_tts can do its own rate mapping if we pass rate="+12%" but for consistency we use librosa 
                # actually let's just stick to time_stretch_audio to avoid edge cases with edge_tts rate bugs
                res = await _synthesize_edge(text, self.voice)
            except Exception as exc:
                logger.warning("edge-tts failed (%s) — falling back to tone", exc)
                res = _synthesize_tone(text)
        else:
            res = _synthesize_tone(text)
            
        if rate != 1.0 and res and res.audio_pcm is not None:
            # librosa-based phase vocoder can create metallic artifacts on
            # ChatterBox output; keep ChatterBox un-stretched for clarity.
            if self._engine_name != "chatterbox-turbo":
                stretched_pcm = time_stretch_audio(res.audio_pcm, res.sample_rate, rate)
                # Recompute duration
                new_dur = len(stretched_pcm) / max(res.sample_rate, 1)
                res.audio_pcm = stretched_pcm
                res.duration_s = new_dur
            
        return res

    async def synthesize_warmup(self) -> None:
        """Force CUDA kernel compilation with a dummy synthesis."""
        if self._engine_name != "chatterbox-turbo":
            return
        logger.info("Performing ChatterBox warmup synthesis …")
        dummy_text = "This is a warm up synthesis to compile CUDA kernels for low latency."
        await self.synthesize(dummy_text)
        logger.info("ChatterBox warmup complete ✓")

    async def synthesize_filler_cache(self) -> list[np.ndarray]:
        """Pre-synthesize natural filler phrases to eliminate start-of-turn gaps."""
        phrases = [
            "right", "okay", "got it", "let me think about that",
            "interesting", "okay so", "right okay", "sure",
            "alright", "I see", "okay let me think", "fair enough",
            "understood", "okay go on", "right and", "sure sure"
        ]
        if self._engine_name != "chatterbox-turbo":
            # Fallback to empty if not using local GPU TTS to avoid blocking startup on edge-tts
            return []

        logger.info("Pre-synthesizing %d filler phrases …", len(phrases))
        t0 = time.perf_counter()
        buffers: list[np.ndarray] = []
        for phrase in phrases:
            res = await self.synthesize(phrase)
            if res.audio_pcm is not None and len(res.audio_pcm) > 0:
                buffers.append(res.audio_pcm)
        
        ms = (time.perf_counter() - t0) * 1000.0
        logger.info("Filler cache ready ✓ (%d clips, %.0fms)", len(buffers), ms)
        return buffers

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
                self._reset_cb_fail_count()
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
