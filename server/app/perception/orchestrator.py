"""
Q&Ace — Parallel Perception Orchestrator.

Architecture per ADR-008:
  - Uses ProcessPoolExecutor with 3 workers for parallel inference.
  - STT (Whisper GPU FP16) + Vocal (Wav2Vec2 GPU FP16) + Face (EfficientNet CPU ONNX)
    all run in parallel on every end-of-speech event.
  - Wall-clock ≤ max(STT, Wav2Vec2, EfficientNet) + 20ms overhead.
  - Models loaded once per worker via initializer function.
  - After parallel perception: BERT text quality runs sequentially (~4ms).
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ProcessPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from ..perception.stt import STTResult
from ..perception.vocal import VocalResult
from ..perception.face import FaceResult
from ..perception.text_quality import TextQualityResult

logger = logging.getLogger("qace.orchestrator")


# ────────────────────────────────────────
# PerceptionResult — unified output
# ────────────────────────────────────────

@dataclass
class PerceptionResult:
    """Unified result from all parallel perception modules."""
    # STT
    transcript: str = ""
    words: list[dict] = field(default_factory=list)
    language: str = "en"
    stt_inference_ms: float = 0.0
    wpm: float = 0.0
    filler_count: int = 0

    # Vocal emotion
    vocal_emotion: str = "neutral"
    vocal_emotion_probs: dict[str, float] = field(default_factory=dict)
    acoustic_confidence: float = 0.0
    pitch_mean_hz: float = 0.0
    pitch_std_hz: float = 0.0
    energy_db: float = 0.0
    vocal_inference_ms: float = 0.0

    # Face emotion
    face_emotion: str = "neutral"
    face_emotion_probs: dict[str, float] = field(default_factory=dict)
    face_confidence: float = 0.0
    face_inference_ms: float = 0.0

    # Text quality (BERT)
    text_quality_label: str = "average"
    text_quality_probs: dict[str, float] = field(default_factory=dict)
    text_quality_score: float = 60.0
    text_quality_inference_ms: float = 0.0

    # AU telemetry (from client DataChannel, not model inference)
    au4: float = 0.0      # brow lowerer
    au12: float = 0.0     # lip corner puller
    au45: float = 0.0     # blink
    eye_contact: float = 0.0

    # Timing
    total_wall_ms: float = 0.0  # total wall-clock for all parallel + sequential
    parallel_wall_ms: float = 0.0  # just the parallel phase


# ────────────────────────────────────────
# Worker functions (run in subprocess)
# ────────────────────────────────────────

# Module-level model references for workers
_worker_whisper = None
_worker_vocal = None
_worker_face = None
_worker_bert = None


def _worker_init(model_dir: str, whisper_model_name: str) -> None:
    """
    Called once in each ProcessPoolExecutor worker process.
    Loads all models into the worker's memory.
    """
    global _worker_whisper, _worker_vocal, _worker_face, _worker_bert
    # Each model load function handles its own error cases
    from ..models.registry import load_whisper, load_silero
    _worker_whisper = load_whisper(model_dir, whisper_model_name)
    # Vocal and face models loaded separately below


def _run_stt(audio_int16: np.ndarray) -> STTResult:
    """Worker function: runs Faster-Whisper STT."""
    from ..perception.stt import transcribe
    from ..models import registry
    return transcribe(audio_int16, registry.whisper_model)


def _run_vocal(audio_int16: np.ndarray) -> VocalResult:
    """Worker function: runs Wav2Vec2 vocal analysis."""
    from ..perception.vocal import analyze
    from ..models import registry
    return analyze(audio_int16, getattr(registry, "vocal_model", None))


def _run_face(face_crop_bytes: bytes, shape: tuple) -> FaceResult:
    """Worker function: runs EfficientNet-B2 face classification."""
    from ..perception.face import classify
    from ..models import registry
    face_crop = np.frombuffer(face_crop_bytes, dtype=np.uint8).reshape(shape)
    return classify(face_crop, getattr(registry, "face_model", None))


# ────────────────────────────────────────
# Orchestrator (runs in main process)
# ────────────────────────────────────────

class PerceptionOrchestrator:
    """
    Orchestrates parallel perception inference.

    For Phase 1/early Phase 2: runs everything in the main process
    with asyncio.run_in_executor (thread pool, simulates parallelism).

    For full Phase 2: uses ProcessPoolExecutor with model-initialized workers.
    """

    def __init__(self, use_process_pool: bool = False, max_workers: int = 3):
        self._use_process_pool = use_process_pool
        self._pool: Optional[ProcessPoolExecutor] = None
        self._max_workers = max_workers

    def start(self, model_dir: str = "", whisper_model: str = "tiny.en") -> None:
        """Initialize the worker pool if using process-based parallelism."""
        if self._use_process_pool:
            self._pool = ProcessPoolExecutor(
                max_workers=self._max_workers,
                initializer=_worker_init,
                initargs=(model_dir, whisper_model),
            )
            logger.info("ProcessPoolExecutor started with %d workers", self._max_workers)

    def shutdown(self) -> None:
        """Shutdown the worker pool."""
        if self._pool:
            self._pool.shutdown(wait=False)
            self._pool = None

    async def run(
        self,
        audio_int16: np.ndarray,
        face_crop: Optional[np.ndarray] = None,
        au_telemetry: Optional[dict] = None,
    ) -> PerceptionResult:
        """
        Run all perception modules in parallel.

        Args:
            audio_int16: int16 @ 16 kHz audio from VAD speech segment.
            face_crop: Optional 224×224 RGB uint8 face crop from latest video frame.
            au_telemetry: Optional latest AU values from client MediaPipe.

        Returns:
            PerceptionResult with all fields populated.
        """
        loop = asyncio.get_running_loop()
        t0 = time.perf_counter()

        # ── Run STT, Vocal, Face in parallel ──
        from ..models import registry
        from ..perception.stt import transcribe
        from ..perception.vocal import analyze as vocal_analyze
        from ..perception.face import classify as face_classify
        from ..perception.text_quality import classify_quality

        # Prepare face crop for transfer (if using process pool, needs serialization)
        face_crop_for_inference = face_crop

        # Launch parallel tasks
        stt_future = loop.run_in_executor(
            self._pool,
            transcribe,
            audio_int16,
            registry.whisper_model,
        )

        vocal_future = loop.run_in_executor(
            self._pool,
            vocal_analyze,
            audio_int16,
            getattr(registry, "vocal_model", None),
        )

        face_future = loop.run_in_executor(
            self._pool,
            face_classify,
            face_crop_for_inference if face_crop_for_inference is not None else np.zeros((224, 224, 3), dtype=np.uint8),
            getattr(registry, "face_model", None),
        )

        # Wait for all parallel tasks
        stt_result, vocal_result, face_result = await asyncio.gather(
            stt_future, vocal_future, face_future,
            return_exceptions=True,
        )

        parallel_ms = (time.perf_counter() - t0) * 1000.0

        # Handle exceptions from parallel tasks
        if isinstance(stt_result, Exception):
            logger.error("STT parallel task failed: %s", stt_result)
            stt_result = STTResult()
        if isinstance(vocal_result, Exception):
            logger.error("Vocal parallel task failed: %s", vocal_result)
            vocal_result = VocalResult()
        if isinstance(face_result, Exception):
            logger.error("Face parallel task failed: %s", face_result)
            face_result = FaceResult()

        # ── Sequential: BERT text quality (runs after STT, needs transcript) ──
        text_quality_result = await loop.run_in_executor(
            None,  # default thread pool
            classify_quality,
            stt_result.text,
            getattr(registry, "bert_model", None),
            getattr(registry, "bert_tokenizer", None),
        )

        total_ms = (time.perf_counter() - t0) * 1000.0

        # ── Assemble PerceptionResult ──
        result = PerceptionResult(
            # STT
            transcript=stt_result.text,
            words=stt_result.words,
            language=stt_result.language,
            stt_inference_ms=stt_result.inference_ms,
            wpm=stt_result.wpm,
            filler_count=stt_result.filler_count,
            # Vocal
            vocal_emotion=vocal_result.dominant_emotion,
            vocal_emotion_probs=vocal_result.emotion_probs,
            acoustic_confidence=vocal_result.acoustic_confidence,
            pitch_mean_hz=vocal_result.pitch_mean_hz,
            pitch_std_hz=vocal_result.pitch_std_hz,
            energy_db=vocal_result.energy_db,
            vocal_inference_ms=vocal_result.inference_ms,
            # Face
            face_emotion=face_result.dominant_emotion,
            face_emotion_probs=face_result.emotion_probs,
            face_confidence=face_result.confidence,
            face_inference_ms=face_result.inference_ms,
            # Text quality
            text_quality_label=text_quality_result.label,
            text_quality_probs=text_quality_result.probabilities,
            text_quality_score=text_quality_result.base_score,
            text_quality_inference_ms=text_quality_result.inference_ms,
            # AU telemetry
            au4=au_telemetry.get("au4", 0.0) if au_telemetry else 0.0,
            au12=au_telemetry.get("au12", 0.0) if au_telemetry else 0.0,
            au45=au_telemetry.get("au45", 0.0) if au_telemetry else 0.0,
            eye_contact=au_telemetry.get("eye_contact", 0.0) if au_telemetry else 0.0,
            # Timing
            total_wall_ms=round(total_ms, 1),
            parallel_wall_ms=round(parallel_ms, 1),
        )

        logger.info(
            "Perception complete: '%s' | vocal=%s | face=%s | quality=%s | "
            "parallel=%.0fms, total=%.0fms (stt=%.0f, vocal=%.0f, face=%.0f, bert=%.0f)",
            result.transcript[:60],
            result.vocal_emotion,
            result.face_emotion,
            result.text_quality_label,
            parallel_ms,
            total_ms,
            result.stt_inference_ms,
            result.vocal_inference_ms,
            result.face_inference_ms,
            result.text_quality_inference_ms,
        )

        return result
