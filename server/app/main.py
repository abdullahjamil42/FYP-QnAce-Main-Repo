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
from .intelligence.rag import init_rag
from .models.registry import prewarm_all

logger = logging.getLogger("qace")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load models. Shutdown: cleanup."""
    logging.basicConfig(
        level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    logger.info("Q&Ace server starting …")
    await prewarm_all()
    # Phase 3: init RAG
    init_rag(get_settings().chroma_dir)
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

    app.include_router(webrtc_router, prefix="/webrtc")
except ImportError as exc:
    logger.warning("WebRTC signaling unavailable (%s)", exc)
