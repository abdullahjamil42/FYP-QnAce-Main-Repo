"""
Q&Ace — Scoring Engine.

Computes per-utterance and running-average scores using the formula:
    Final = 0.70 × Content + 0.20 × Delivery + 0.10 × Composure

Each sub-score is in [0, 100].

Content  = BERT quality base_score + optional LLM STAR modifier (±10)
Delivery = 0.50 × fluency(WPM, fillers) + 0.50 × wav2vec2_confidence
Composure = 0.60 × eye_contact + 0.25 × (1 - blink_deviation) + 0.15 × emotion_positivity
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("qace.scoring")


@dataclass
class UtteranceScores:
    """Per-utterance score breakdown."""
    content: float = 0.0
    delivery: float = 0.0
    composure: float = 0.0
    final: float = 0.0

    # Sub-components (for debugging / results page)
    fluency: float = 0.0
    vocal_confidence: float = 0.0
    eye_contact: float = 0.0
    blink_deviation: float = 0.0
    emotion_positivity: float = 0.0
    text_quality_score: float = 0.0


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def compute_fluency(wpm: float, filler_count: int, duration_s: float = 60.0) -> float:
    """
    Fluency score (0-100).
    Sweet spot: 130-160 WPM. Penalty for fillers.
    """
    if 130 <= wpm <= 160:
        wpm_score = 100.0
    elif 120 <= wpm < 130 or 160 < wpm <= 180:
        wpm_score = 80.0
    elif 100 <= wpm < 120 or 180 < wpm <= 200:
        wpm_score = 60.0
    else:
        wpm_score = 40.0

    fillers_per_min = filler_count / max(duration_s / 60.0, 1.0)
    filler_penalty = min(fillers_per_min * 5.0, 40.0)

    return clamp(wpm_score - filler_penalty)


def compute_composure(
    eye_contact_ratio: float,
    blinks_per_min: float,
    emotion_positivity: float,
) -> float:
    """Composure score (0-100)."""
    blink_deviation = abs(blinks_per_min - 17.5) / 17.5
    composure = (
        0.60 * eye_contact_ratio * 100
        + 0.25 * max(0, 1.0 - blink_deviation) * 100
        + 0.15 * emotion_positivity * 100
    )
    return clamp(composure)


def compute_utterance_scores(
    text_quality_score: float = 60.0,
    wpm: float = 0.0,
    filler_count: int = 0,
    duration_s: float = 3.0,
    vocal_confidence: float = 0.0,
    eye_contact_ratio: float = 0.5,
    blinks_per_min: float = 17.5,
    emotion_positivity: float = 0.5,
    llm_modifier: float = 0.0,
) -> UtteranceScores:
    """
    Compute scores for a single utterance.

    Args:
        text_quality_score: BERT base score (0-100), or heuristic fallback.
        wpm: Words per minute from STT.
        filler_count: Number of filler words detected.
        duration_s: Audio duration in seconds.
        vocal_confidence: Wav2Vec2 acoustic confidence (0-1).
        eye_contact_ratio: Eye contact ratio (0-1) from AU telemetry.
        blinks_per_min: Blink rate from AU telemetry.
        emotion_positivity: Positive emotion score (0-1).
        llm_modifier: Optional LLM STAR analysis modifier (±10).
    """
    # Content (70%)
    content = clamp(text_quality_score + llm_modifier)

    # Delivery (20%)
    fluency = compute_fluency(wpm, filler_count, duration_s)
    delivery = clamp(0.50 * fluency + 0.50 * vocal_confidence * 100)

    # Composure (10%)
    composure = compute_composure(eye_contact_ratio, blinks_per_min, emotion_positivity)

    # Final weighted
    final = clamp(0.70 * content + 0.20 * delivery + 0.10 * composure)

    scores = UtteranceScores(
        content=round(content, 1),
        delivery=round(delivery, 1),
        composure=round(composure, 1),
        final=round(final, 1),
        fluency=round(fluency, 1),
        vocal_confidence=round(vocal_confidence, 3),
        eye_contact=round(eye_contact_ratio, 3),
        blink_deviation=round(abs(blinks_per_min - 17.5) / 17.5, 3),
        emotion_positivity=round(emotion_positivity, 3),
        text_quality_score=round(text_quality_score, 1),
    )

    logger.info(
        "Scores: content=%.1f delivery=%.1f composure=%.1f → final=%.1f",
        scores.content, scores.delivery, scores.composure, scores.final,
    )
    return scores


class RunningScorer:
    """Maintains running average across multiple utterances."""

    def __init__(self):
        self._history: list[UtteranceScores] = []

    def add(self, scores: UtteranceScores) -> None:
        self._history.append(scores)

    @property
    def count(self) -> int:
        return len(self._history)

    @property
    def latest(self) -> Optional[UtteranceScores]:
        return self._history[-1] if self._history else None

    @property
    def average(self) -> UtteranceScores:
        """Compute running average of all utterance scores."""
        if not self._history:
            return UtteranceScores()

        n = len(self._history)
        avg = UtteranceScores(
            content=round(sum(s.content for s in self._history) / n, 1),
            delivery=round(sum(s.delivery for s in self._history) / n, 1),
            composure=round(sum(s.composure for s in self._history) / n, 1),
            final=round(sum(s.final for s in self._history) / n, 1),
        )
        return avg

    def to_dict(self) -> dict:
        """Return latest + average scores as a dict for DataChannel delivery."""
        latest = self.latest or UtteranceScores()
        avg = self.average
        return {
            "content": latest.content,
            "delivery": latest.delivery,
            "composure": latest.composure,
            "final": latest.final,
            "avg_content": avg.content,
            "avg_delivery": avg.delivery,
            "avg_composure": avg.composure,
            "avg_final": avg.final,
            "utterance_count": self.count,
        }
