"""
Q&Ace — Pydantic Settings (environment-driven configuration).
Loaded once at import time; values come from .env or environment variables.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # server/app/config.py → repo root


class Settings(BaseSettings):
    # ── General ──
    env: str = Field("development", alias="QACE_ENV")
    host: str = Field("0.0.0.0", alias="QACE_HOST")
    port: int = Field(8000, alias="QACE_PORT")
    log_level: str = Field("info", alias="QACE_LOG_LEVEL")

    # ── CORS ──
    cors_origins: str = Field(
        "http://localhost:3000,http://127.0.0.1:3000",
        alias="QACE_CORS_ORIGINS",
    )

    # ── LLM Providers ──
    llm_provider: str = Field("auto", alias="QACE_LLM_PROVIDER")
    groq_api_key: str = Field("", alias="GROQ_API_KEY")
    airforce_api_key: str = Field("", alias="AIRFORCE_API_KEY")

    # ── Models ──
    model_dir: str = Field(str(_REPO_ROOT / "models"), alias="QACE_MODEL_DIR")
    whisper_model: str = Field("tiny.en", alias="QACE_WHISPER_MODEL")
    silero_onnx: str = Field(
        str(_REPO_ROOT / "models" / "silero-vad" / "silero_vad.onnx"),
        alias="QACE_SILERO_ONNX",
    )

    # ── Phase 2: Perception models ──
    vocal_model_name: str = Field(
        "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition",
        alias="QACE_VOCAL_MODEL",
    )
    vocal_device: str = Field("auto", alias="QACE_VOCAL_DEVICE")
    face_onnx: str = Field(
        str(_REPO_ROOT / "models" / "face-emotion" / "efficientnet_b2.onnx"),
        alias="QACE_FACE_ONNX",
    )
    bert_onnx: str = Field(
        str(_REPO_ROOT / "models" / "text-quality" / "bert_quality.onnx"),
        alias="QACE_BERT_ONNX",
    )
    bert_tokenizer: str = Field(
        "bert-base-uncased",
        alias="QACE_BERT_TOKENIZER",
    )

    # ── Phase 3: Intelligence / RAG ──
    chroma_dir: str = Field(
        str(_REPO_ROOT / "data" / "chroma"),
        alias="QACE_CHROMA_DIR",
    )
    llm_model: str = Field("", alias="QACE_LLM_MODEL")
    groq_model: str = Field("llama-3.3-70b-versatile", alias="QACE_GROQ_MODEL")
    airforce_model: str = Field("gpt-4o-mini", alias="QACE_AIRFORCE_MODEL")

    # ── Phase 4: Synthesis ──
    tts_voice: str = Field("en-US-GuyNeural", alias="QACE_TTS_VOICE")
    tts_backend: str = Field("auto", alias="QACE_TTS_BACKEND")
    chatterbox_device: str = Field("auto", alias="QACE_CHATTERBOX_DEVICE")
    avatar_image: str = Field(
        str(_REPO_ROOT / "models" / "avatar" / "interviewer.png"),
        alias="QACE_AVATAR_IMAGE",
    )
    avatar_fps: int = Field(30, alias="QACE_AVATAR_FPS")

    # ── VAD ──
    vad_silence_ms: int = Field(300, alias="QACE_VAD_SILENCE_MS")
    vad_min_speech_s: float = Field(1.0, alias="QACE_VAD_MIN_SPEECH_S")

    model_config = {"env_file": str(_REPO_ROOT / ".env"), "extra": "ignore"}

    # ── Derived helpers ──
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def normalized_llm_provider(self) -> str:
        return self.llm_provider.strip().lower()


@lru_cache()
def get_settings() -> Settings:
    return Settings()
