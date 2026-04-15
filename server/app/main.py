"""
Q&Ace — FastAPI application entry-point.

- Lifespan hook pre-warms all AI models at startup (zero cold-start latency).
- CORS configured for local frontend.
- All WebRTC / REST routes mounted here.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .intelligence.llm import check_local_llm_endpoint
from .intelligence.rag import init_rag
from .models.registry import prewarm_all
from .runtime.cudnn_guard import apply_global_cudnn_guard

logger = logging.getLogger("qace")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load models. Shutdown: cleanup."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    logger.info("Q&Ace server starting …")
    apply_global_cudnn_guard()

    if settings.normalized_llm_provider == "local":
        if settings.local_llm_base_url.strip():
            ok, detail = check_local_llm_endpoint(settings.local_llm_base_url)
            if ok:
                logger.info("Local LLM endpoint mode ✓ %s", detail)
            else:
                logger.warning("Local LLM endpoint mode ✗ %s", detail)
        elif settings.local_llm_base_model.strip() and settings.local_llm_adapter_path.strip():
            logger.info(
                "Local LLM PEFT mode ✓ base=%s adapter=%s",
                settings.local_llm_base_model,
                settings.local_llm_adapter_path,
            )
        else:
            logger.info("Local LLM model-path mode ✓ path=%s", settings.local_llm_path)

    await prewarm_all()
    # Phase 3: init RAG
    init_rag(settings.chroma_dir, settings.rag_embed_device)
    yield
    logger.info("Q&Ace server shutting down.")


app = FastAPI(
    title="Q&Ace API",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──
@app.get("/health")
async def health():
    from .models import registry

    return {
        "status": "ok",
        "env": settings.env,
        "models": {
            "whisper": type(registry.whisper_model).__name__ if registry.whisper_model else None,
            "silero_vad": type(registry.silero_vad).__name__ if registry.silero_vad else None,
            "vocal": type(registry.vocal_model).__name__ if registry.vocal_model else None,
            "face": type(registry.face_model).__name__ if registry.face_model else None,
            "bert": type(registry.bert_model).__name__ if registry.bert_model else None,
        },
    }


# ── WebRTC signaling route (lazy import to avoid hard dep on aiortc) ──
try:
    from .webrtc.signaling import router as webrtc_router
    from .webrtc.cv_routes import cv_router
    from .webrtc.report_routes import report_router

    app.include_router(webrtc_router, prefix="/webrtc")
    app.include_router(cv_router, prefix="/api/cv")
    app.include_router(report_router, prefix="/api/report")
except ImportError as exc:
    logger.warning("WebRTC signaling unavailable (%s)", exc)
