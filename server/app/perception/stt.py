"""
Q&Ace — Faster-Whisper STT wrapper.

Architecture per ADR-002:
  - distil-large-v3, FP16, beam_size=1 (greedy), ~140 ms on RTX 4090.
  - Runs inside ProcessPoolExecutor worker (Phase 2), called directly in Phase 1.
  - Input: int16 numpy array @ 16 kHz.
  - Output: transcript text + word-level timestamps + metrics.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("qace.stt")


@dataclass
class STTResult:
    text: str = ""
    words: list[dict] = field(default_factory=list)  # [{word, start, end, probability}]
    language: str = "en"
    inference_ms: float = 0.0
    wpm: float = 0.0
    filler_count: int = 0


# Common filler words for interview context
FILLER_WORDS = {"um", "uh", "uhm", "umm", "er", "ah", "like", "you know", "basically", "actually"}


def transcribe(audio: np.ndarray, whisper_model: Any) -> STTResult:
    """
    Transcribe int16 @ 16 kHz audio using Faster-Whisper.

    Returns STTResult with text, word timestamps, WPM, and filler count.
    Falls back to empty result if model is unavailable.
    """
    if whisper_model is None:
        logger.warning("Whisper model not loaded — returning empty transcript")
        return STTResult()

    # Convert int16 → float32 normalised [-1, 1]
    audio_f32 = audio.astype(np.float32) / 32768.0
    duration_s = len(audio_f32) / 16_000

    t0 = time.perf_counter()
    try:
        logger.info("STT start: %.2fs audio", duration_s)
        segments, info = whisper_model.transcribe(
            audio_f32,
            beam_size=1,  # greedy — per ADR-002
            language="en",
            word_timestamps=False,
            condition_on_previous_text=False,
            vad_filter=False,  # we do our own VAD
        )
        # Materialise generator
        segments = list(segments)
    except Exception as exc:
        logger.error("Whisper transcribe error: %s", exc)
        return STTResult()

    inference_ms = (time.perf_counter() - t0) * 1000.0

    # Build result
    full_text_parts: list[str] = []
    words: list[dict] = []
    filler_count = 0

    for seg in segments:
        full_text_parts.append(seg.text.strip())
        if getattr(seg, "words", None):
            for w in seg.words:
                word_lower = w.word.strip().lower()
                words.append(
                    {
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "probability": round(w.probability, 3),
                    }
                )
                if word_lower in FILLER_WORDS:
                    filler_count += 1

    full_text = " ".join(full_text_parts).strip()
    word_count = len(full_text.split()) if full_text else 0
    wpm = (word_count / duration_s * 60.0) if duration_s > 0 else 0.0

    logger.info(
        "STT: '%s' (%.0f ms, %d words, %.0f WPM, %d fillers)",
        full_text[:80],
        inference_ms,
        word_count,
        wpm,
        filler_count,
    )

    return STTResult(
        text=full_text,
        words=words,
        language=info.language if hasattr(info, "language") else "en",
        inference_ms=round(inference_ms, 1),
        wpm=round(wpm, 1),
        filler_count=filler_count,
    )
