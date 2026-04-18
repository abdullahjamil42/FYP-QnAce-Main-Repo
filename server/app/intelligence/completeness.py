"""
Q&Ace — Answer Completeness Evaluation.

Orchestrates three scoring signals into a composite completeness score:
  - Signal A (50%): Semantic — LLM judges if the answer feels complete
  - Signal B (30%): Prosodic — pitch slope + energy drop
  - Signal C (20%): Coverage — structural element detection

Used by signaling.py to decide when to advance to the next question.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger("qace.completeness")


@dataclass
class CompletenessResult:
    """Result of the multi-signal completeness evaluation."""

    score: float           # weighted composite 0.0-1.0
    semantic: float        # Signal A (weight 0.50)
    prosodic: float        # Signal B (weight 0.30)
    coverage: float        # Signal C (weight 0.20)
    should_advance: bool   # score >= 0.70


# ── Weights ──────────────────────────────────────────────────────────────

_W_SEMANTIC = 0.50
_W_PROSODIC = 0.30
_W_COVERAGE = 0.20
_ADVANCE_THRESHOLD = 0.70


# ── Semantic scoring (Signal A) ──────────────────────────────────────────

_SEMANTIC_SYS = "You are evaluating interview answers. Return only valid JSON."

_SEMANTIC_USER = (
    "Question asked: {question}\n"
    "Answer so far: {answer}\n\n"
    "Does this answer feel complete — like the speaker has reached a natural "
    "conclusion — or does it feel mid-thought and unfinished?\n\n"
    'Return JSON: {{ "complete": true/false, "score": 0.0-1.0, '
    '"reason": "..." }}\n'
    "Score 1.0 = clearly finished, 0.0 = clearly mid-sentence."
)

_SCORE_REGEX = re.compile(r'"score"\s*:\s*([0-9]*\.?[0-9]+)')


async def _evaluate_semantic(
    full_transcript: str,
    question_text: str,
    provider_config: Any,
) -> float:
    """LLM-based semantic completeness score (0.0-1.0). Fallback: 0.5."""
    from .llm import call_llm

    user_msg = _SEMANTIC_USER.format(
        question=question_text,
        answer=full_transcript,
    )

    response = await call_llm(
        messages=[
            {"role": "system", "content": _SEMANTIC_SYS},
            {"role": "user", "content": user_msg},
        ],
        provider_config=provider_config,
        temperature=0.2,
        max_tokens=128,
        timeout_s=3.0,
    )

    if not response:
        logger.debug("Semantic completeness: LLM returned None, fallback 0.5")
        return 0.5

    # Try JSON parsing first
    try:
        data = json.loads(response)
        score = float(data.get("score", 0.5))
        return max(0.0, min(1.0, score))
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Regex fallback
    match = _SCORE_REGEX.search(response)
    if match:
        try:
            return max(0.0, min(1.0, float(match.group(1))))
        except ValueError:
            pass

    logger.debug("Semantic completeness: could not parse LLM response, fallback 0.5")
    return 0.5


# ── Prosodic scoring (Signal B) ──────────────────────────────────────────

def _evaluate_prosodic(audio_tail: np.ndarray, sample_rate: int) -> float:
    """Prosodic finality score based on pitch slope + energy drop."""
    from ..perception.vocal import analyze_finality

    pitch_slope, energy_drop = analyze_finality(audio_tail, sample_rate)

    if pitch_slope < -0.3 and energy_drop < 0.6:
        return 1.0   # strong ending cues
    elif pitch_slope < -0.1 or energy_drop < 0.6:
        return 0.6   # moderate ending cues
    else:
        return 0.2   # no clear ending cues


# ── Main orchestrator ────────────────────────────────────────────────────

async def evaluate_completeness(
    full_transcript: str,
    question_text: str,
    question_subtype: str,
    audio_tail: np.ndarray,
    sample_rate: int,
    provider_config: Any,
) -> CompletenessResult:
    """
    Evaluate answer completeness using three parallel signals.

    Signal A (semantic, LLM) runs concurrently with Signals B+C
    (pure computation) via ``asyncio.gather()``.
    """
    from .coverage import compute_coverage_score

    # Run semantic (async LLM) concurrently with prosodic + coverage (sync)
    async def _sync_signals() -> tuple[float, float]:
        prosodic = _evaluate_prosodic(audio_tail, sample_rate)
        coverage = compute_coverage_score(full_transcript, question_subtype)
        return prosodic, coverage

    semantic_score, (prosodic_score, coverage_score) = await asyncio.gather(
        _evaluate_semantic(full_transcript, question_text, provider_config),
        _sync_signals(),
    )

    composite = (
        semantic_score * _W_SEMANTIC
        + prosodic_score * _W_PROSODIC
        + coverage_score * _W_COVERAGE
    )

    result = CompletenessResult(
        score=round(composite, 3),
        semantic=round(semantic_score, 3),
        prosodic=round(prosodic_score, 3),
        coverage=round(coverage_score, 3),
        should_advance=composite >= _ADVANCE_THRESHOLD,
    )

    logger.info(
        "Completeness: score=%.2f (sem=%.2f pro=%.2f cov=%.2f) advance=%s",
        result.score, result.semantic, result.prosodic, result.coverage,
        result.should_advance,
    )

    return result
