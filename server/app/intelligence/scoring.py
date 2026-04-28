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


def _wpm_score(wpm: float) -> float:
    """
    Research-aligned WPM score (0-100).
    Sweet spot 140–160 WPM (professional interview standard, Huru research).
    Slow and fast are penalised asymmetrically: slow risks disengagement,
    fast (>190 WPM) degrades comprehension 17–25% (Tctecinnovation research).
    """
    if wpm == 0:
        return 0.0
    if 140 <= wpm <= 160:    # research-confirmed sweet spot
        return 100.0
    if 130 <= wpm < 140:     # slightly slow — still professional
        return 85.0
    if 160 < wpm <= 175:     # fast but energetic — acceptable
        return 80.0
    if 120 <= wpm < 130:     # noticeably slow — some disengagement risk
        return 65.0
    if 175 < wpm <= 195:     # fast, comprehension starts dropping
        return 60.0
    if 100 <= wpm < 120:     # too slow — audience tunes out
        return 45.0
    if 195 < wpm <= 220:     # comprehension significantly impacted
        return 35.0
    return 20.0              # extreme outliers


def compute_fluency(wpm: float, filler_count: int, duration_s: float = 60.0) -> float:
    """
    Fluency score (0-100).
    Sweet spot: 140-160 WPM. Filler penalty is rate-based (per minute).
    """
    wpm_score = _wpm_score(wpm)

    fillers_per_min = filler_count / max(duration_s / 60.0, 1.0)
    filler_penalty = min(fillers_per_min * 5.0, 40.0)

    return clamp(wpm_score - filler_penalty)


def compute_composure(
    eye_contact_ratio: float,
    blinks_per_min: float,
    emotion_positivity: float,
) -> float:
    """Composure score (0-100).

    Weights (research-backed):
      0.40 eye contact      — reduced from 0.60; single MediaPipe ratio is fragile
                              (camera angle, lighting, glasses all affect it)
      0.25 blink norm       — unchanged
      0.35 emotion          — raised from 0.15; multimodal engagement signals
                              correlate r=0.73+ with hiring ratings (U. Rochester)
    """
    blink_deviation = abs(blinks_per_min - 17.5) / 17.5
    composure = (
        0.40 * eye_contact_ratio * 100
        + 0.25 * max(0, 1.0 - blink_deviation) * 100
        + 0.35 * emotion_positivity * 100
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

    # Delivery (20%) — fluency weighted higher; acoustic confidence is a narrower signal
    fluency = compute_fluency(wpm, filler_count, duration_s)
    delivery = clamp(0.65 * fluency + 0.35 * vocal_confidence * 100)

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


class InterviewScoringEngine:
    """Compatibility scoring engine used by WebRTC signaling pipeline.

    The signaling route expects a structured dict with `Sub_Scores`,
    `Final_Score`, `Deduction_Flags`, and `Details`. This adapter builds
    that payload from the scoring helpers in this module.
    """

    def evaluate_session(self, telemetry: dict) -> dict:
        text_quality_score = float(telemetry.get("bert_base_score", 60.0) or 60.0)
        wpm = float(telemetry.get("whisper_wpm", 0.0) or 0.0)
        filler_count = int(telemetry.get("whisper_filler_count", 0) or 0)
        duration_s = float(telemetry.get("whisper_duration_s", 3.0) or 3.0)
        vocal_confidence = float(telemetry.get("wav2vec2_confidence", 0.0) or 0.0)
        eye_contact = float(telemetry.get("mediapipe_eye_contact", 0.5) or 0.5)
        blinks_per_min = float(telemetry.get("mediapipe_bpm", 17.5) or 17.5)

        emotion_timeline = telemetry.get("emotion_timeline") or []
        emotion_positivity = 0.5
        if isinstance(emotion_timeline, list) and emotion_timeline:
            maybe = emotion_timeline[-1]
            if isinstance(maybe, (int, float)):
                emotion_positivity = max(0.0, min(1.0, float(maybe)))

        llm_star = telemetry.get("llm_star_evaluation", text_quality_score)
        raw_modifier = float(llm_star) - text_quality_score
        # Fix 4: Variable cap by question type — LLM is most reliable for STAR
        # behavioral answers; BERT + RAG are more reliable for technical ones.
        q_subtype = telemetry.get("question_subtype", "unknown")
        if q_subtype == "behavioral":
            llm_modifier = max(-20.0, min(15.0, raw_modifier))
        elif q_subtype == "technical":
            llm_modifier = max(-10.0, min(10.0, raw_modifier))
        else:
            llm_modifier = max(-12.0, min(12.0, raw_modifier))

        scores = compute_utterance_scores(
            text_quality_score=text_quality_score,
            wpm=wpm,
            filler_count=filler_count,
            duration_s=duration_s,
            vocal_confidence=vocal_confidence,
            eye_contact_ratio=eye_contact,
            blinks_per_min=blinks_per_min,
            emotion_positivity=emotion_positivity,
            llm_modifier=llm_modifier,
        )

        deduction_flags: list[str] = []
        if (filler_count / max(duration_s / 60.0, 0.5)) >= 4.0:  # rate-based: ≥4 fillers/min
            deduction_flags.append("high_fillers")
        if wpm > 190:
            deduction_flags.append("too_fast")
        elif 0 < wpm < 105:
            deduction_flags.append("too_slow")
        if eye_contact < 0.35:
            deduction_flags.append("low_eye_contact")

        return {
            "Sub_Scores": {
                "Content": scores.content,
                "Delivery": scores.delivery,
                "Composure": scores.composure,
            },
            "Final_Score": scores.final,
            "Deduction_Flags": deduction_flags,
            "Details": {
                "fluency": scores.fluency,
                "wpm": wpm,
                "filler_count": filler_count,
                "eye_contact": eye_contact,
                "vocal_confidence": vocal_confidence,
                "text_quality_score": text_quality_score,
            },
        }
