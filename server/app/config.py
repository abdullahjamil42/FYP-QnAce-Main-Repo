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
    rag_embed_device: str = Field("cpu", alias="QACE_RAG_EMBED_DEVICE")
    llm_model: str = Field("", alias="QACE_LLM_MODEL")
    llm_max_tokens: int = Field(120, alias="QACE_LLM_MAX_TOKENS")
    groq_model: str = Field("llama-3.3-70b-versatile", alias="QACE_GROQ_MODEL")
    airforce_model: str = Field("gpt-4o-mini", alias="QACE_AIRFORCE_MODEL")
    local_llm_path: str = Field(
        str(_REPO_ROOT / "Llama_3.1_fine_Tuned"),
        alias="QACE_LOCAL_LLM_PATH",
    )
    local_llm_base_model: str = Field("", alias="QACE_LOCAL_LLM_BASE_MODEL")
    local_llm_adapter_path: str = Field(
        str(_REPO_ROOT / "Llama_3.1_fine_Tuned" / "qace-llm-package" / "adapters" / "evaluator"),
        alias="QACE_LOCAL_LLM_ADAPTER_PATH",
    )
    local_llm_base_url: str = Field("", alias="QACE_LOCAL_LLM_BASE_URL")
    local_llm_api_key: str = Field("", alias="QACE_LOCAL_LLM_API_KEY")
    local_llm_device: str = Field("auto", alias="QACE_LOCAL_LLM_DEVICE")
    local_llm_dtype: str = Field("auto", alias="QACE_LOCAL_LLM_DTYPE")
    interviewer_classifier_model: str = Field(
        "llama-3.1-8b-instant",
        alias="QACE_INTERVIEWER_CLASSIFIER_MODEL",
    )
    interviewer_generator_model: str = Field(
        "llama-3.3-70b-versatile",
        alias="QACE_INTERVIEWER_GENERATOR_MODEL",
    )
    interviewer_classifier_temperature: float = Field(
        0.0,
        alias="QACE_INTERVIEWER_CLASSIFIER_TEMPERATURE",
    )
    interviewer_classifier_max_tokens: int = Field(
        150,
        alias="QACE_INTERVIEW_CLASSIFIER_MAX_TOKENS",
    )
    interviewer_history_window: int = Field(3, alias="QACE_INTERVIEWER_HISTORY_WINDOW")
    interviewer_summary_max_chars: int = Field(
        1200,
        alias="QACE_INTERVIEWER_SUMMARY_MAX_CHARS",
    )
    interview_interrupt_word_limit: int = Field(250, alias="QACE_INTERVIEW_INTERRUPT_WORD_LIMIT")

    # ── Phase 4: Synthesis ──
    tts_voice: str = Field("en-US-GuyNeural", alias="QACE_TTS_VOICE")
    tts_backend: str = Field("auto", alias="QACE_TTS_BACKEND")
    chatterbox_device: str = Field("auto", alias="QACE_CHATTERBOX_DEVICE")
    tts_sentence_streaming: bool = Field(True, alias="QACE_TTS_SENTENCE_STREAMING")
    tts_chunk_max_chars: int = Field(150, alias="QACE_TTS_CHUNK_MAX_CHARS")
    chatterbox_compile: bool = Field(True, alias="QACE_CHATTERBOX_COMPILE")
    chatterbox_half: bool = Field(True, alias="QACE_CHATTERBOX_HALF")
    avatar_image: str = Field(
        str(_REPO_ROOT / "models" / "avatar" / "interviewer.png"),
        alias="QACE_AVATAR_IMAGE",
    )
    avatar_fps: int = Field(30, alias="QACE_AVATAR_FPS")

    # ── VAD ──
    vad_silence_ms: int = Field(300, alias="QACE_VAD_SILENCE_MS")
    vad_min_speech_s: float = Field(1.0, alias="QACE_VAD_MIN_SPEECH_S")
    semantic_vad_enabled: bool = Field(True, alias="QACE_SEMANTIC_VAD_ENABLED")
    semantic_min_silence_ms: int = Field(400, alias="QACE_SEMANTIC_MIN_SILENCE_MS")
    semantic_max_silence_ms: int = Field(1500, alias="QACE_SEMANTIC_MAX_SILENCE_MS")
    semantic_threshold: float = Field(0.85, alias="QACE_SEMANTIC_THRESHOLD")
    semantic_model: str = Field(
        "distilbert-base-uncased-finetuned-sst-2-english",
        alias="QACE_SEMANTIC_MODEL",
    )

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
