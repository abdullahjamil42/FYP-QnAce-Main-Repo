"""Runtime model registry for Q&Ace backend.

This module centralizes optional model loading so the API can start even when
some heavy artifacts are unavailable. Callers should handle `None` models.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from ..config import get_settings

logger = logging.getLogger("qace.models")

# Shared model handles
whisper_model: Any = None
whisper_model_device: str | None = None
silero_vad: Any = None
vocal_model: Any = None
face_model: Any = None
bert_model: Any = None
bert_tokenizer: Any = None
tts_engine: Any = None
avatar_engine: Any = None


def load_whisper(model_dir: str, model_name: str, *, device: str = "auto") -> Any:
    """Load Faster-Whisper model, returning `None` on failure."""
    global whisper_model_device
    try:
        from faster_whisper import WhisperModel

        device_candidates: list[str]
        if device == "auto":
            device_candidates = ["cuda", "cpu"]
        elif device == "cuda":
            device_candidates = ["cuda", "cpu"]
        else:
            device_candidates = [device]

        last_exc: Exception | None = None
        for selected in device_candidates:
            compute_type = "float16" if selected == "cuda" else "int8"
            try:
                model = WhisperModel(
                    model_name,
                    device=selected,
                    compute_type=compute_type,
                    download_root=str(model_dir),
                )
                whisper_model_device = selected
                logger.info("Whisper loaded: %s (%s)", model_name, selected)
                return model
            except Exception as exc:
                last_exc = exc
                logger.warning("Whisper load failed on %s (%s)", selected, exc)

        logger.warning("Whisper unavailable after retries (%s)", last_exc)
        whisper_model_device = None
        return None
    except Exception as exc:
        logger.warning("Whisper load failed (%s) — using empty fallback", exc)
        whisper_model_device = None
        return None


def load_whisper_cpu(model_dir: str, model_name: str) -> Any:
    """Force-load Whisper on CPU for timeout fallback flow."""
    return load_whisper(model_dir, model_name, device="cpu")


def load_silero(model_dir: str, silero_onnx_path: str | None = None) -> Any:
    """Load Silero VAD ONNX session from configured path."""
    try:
        import onnxruntime as ort

        path = Path(silero_onnx_path) if silero_onnx_path else Path(model_dir) / "silero-vad" / "silero_vad.onnx"
        if not path.exists():
            logger.warning("Silero model not found at %s", path)
            return None

        available = set(ort.get_available_providers())
        providers = [p for p in ["CUDAExecutionProvider", "CPUExecutionProvider"] if p in available]
        if not providers:
            providers = ["CPUExecutionProvider"]
        session = ort.InferenceSession(str(path), providers=providers)
        logger.info("Silero VAD loaded: %s", path)
        return session
    except Exception as exc:
        logger.warning("Silero load failed (%s)", exc)
        return None


def load_face(face_onnx: str) -> Any:
    """Load face ONNX model when present."""
    try:
        import onnxruntime as ort

        path = Path(face_onnx)
        if not path.exists():
            logger.info("Face ONNX not found at %s (optional)", path)
            return None
        available = set(ort.get_available_providers())
        providers = [p for p in ["CUDAExecutionProvider", "CPUExecutionProvider"] if p in available]
        if not providers:
            providers = ["CPUExecutionProvider"]
        return ort.InferenceSession(str(path), providers=providers)
    except Exception as exc:
        logger.warning("Face model load failed (%s)", exc)
        return None


def load_bert(bert_onnx: str, tokenizer_name: str) -> tuple[Any, Any]:
    """Load ONNX text-quality model and tokenizer when available."""
    try:
        import onnxruntime as ort
    except Exception as exc:
        logger.warning("onnxruntime unavailable for BERT (%s)", exc)
        return None, None

    model = None
    tokenizer = None
    try:
        path = Path(bert_onnx)
        if path.exists():
            available = set(ort.get_available_providers())
            providers = [p for p in ["CUDAExecutionProvider", "CPUExecutionProvider"] if p in available]
            if not providers:
                providers = ["CPUExecutionProvider"]
            model = ort.InferenceSession(str(path), providers=providers)
        else:
            logger.info("BERT ONNX not found at %s (heuristic fallback will be used)", path)
    except Exception as exc:
        logger.warning("BERT ONNX load failed (%s)", exc)

    try:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    except Exception as exc:
        logger.warning("BERT tokenizer load failed (%s)", exc)

    return model, tokenizer


def _load_vocal_model(model_name: str, device_pref: str = "auto") -> Any:
    """Load Wav2Vec2 vocal model when available."""
    try:
        import torch
        from transformers import AutoModelForAudioClassification

        if device_pref == "auto":
            candidates = ["cuda", "cpu"] if torch.cuda.is_available() else ["cpu"]
        elif device_pref == "cuda":
            candidates = ["cuda", "cpu"]
        else:
            candidates = [device_pref]

        model = AutoModelForAudioClassification.from_pretrained(model_name)
        last_exc: Exception | None = None
        for device in candidates:
            try:
                dtype = torch.float16 if device == "cuda" else torch.float32
                loaded = model.to(device=device, dtype=dtype).eval()
                logger.info("Vocal model loaded: %s (%s)", model_name, device)
                return loaded
            except Exception as exc:
                last_exc = exc
                logger.warning("Vocal model load failed on %s (%s)", device, exc)

        logger.warning("Vocal model unavailable after retries (%s)", last_exc)
        return None
    except Exception as exc:
        logger.warning("Vocal model load failed (%s)", exc)
        return None


async def prewarm_all() -> None:
    """Load core runtime models best-effort for lower first-turn latency."""
    global whisper_model, silero_vad, vocal_model, face_model, bert_model, bert_tokenizer
    global tts_engine, avatar_engine

    settings = get_settings()
    loop = asyncio.get_running_loop()

    from ..synthesis.avatar import create_avatar_engine
    from ..synthesis.tts import create_tts_engine

    whisper_model = await loop.run_in_executor(
        None,
        load_whisper,
        settings.model_dir,
        settings.whisper_model,
    )
    silero_vad = await loop.run_in_executor(
        None,
        load_silero,
        settings.model_dir,
        settings.silero_onnx,
    )
    vocal_model = await loop.run_in_executor(
        None,
        _load_vocal_model,
        settings.vocal_model_name,
        settings.vocal_device,
    )
    face_model = await loop.run_in_executor(None, load_face, settings.face_onnx)
    bert_model, bert_tokenizer = await loop.run_in_executor(
        None,
        load_bert,
        settings.bert_onnx,
        settings.bert_tokenizer,
    )

    # Phase 4: synthesis runtime (TTS + avatar)
    tts_engine = await loop.run_in_executor(
        None,
        create_tts_engine,
        settings.tts_voice,
        settings.tts_backend,
        settings.chatterbox_device,
    )

    avatar_engine = await loop.run_in_executor(
        None,
        create_avatar_engine,
        settings.avatar_image,
    )

    try:
        if avatar_engine is not None:
            avatar_engine.precompute_source_features()
    except Exception as exc:
        logger.warning("Avatar source precompute failed (%s)", exc)
