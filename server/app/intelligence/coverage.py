"""
Q&Ace — Question Coverage Scoring.

Provides:
  - ``classify_question_subtype()`` — LLM-based sub-classification
    (behavioral / technical / situational).
  - ``compute_coverage_score()`` — regex/keyword heuristic that checks
    whether the candidate's transcript contains expected structural
    elements for the detected subtype.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("qace.coverage")

# ── Structural elements expected per subtype ─────────────────────────────

# STAR-component patterns for behavioral questions.
# Action is weighted 2× (0.40) — it's the substance of the answer.
_BEHAVIORAL_STAR: dict[str, list[str]] = {
    "situation": [
        r"\b(when|during|at the time|in \d{4}|last (year|month|quarter))\b",
        r"\b(we were|our team|I was working|my role was)\b",
    ],
    "task": [
        r"\b(my (responsibility|job|goal|objective) was|I (had to|needed to|was tasked))\b",
        r"\b(the (problem|challenge|issue) was|we needed to)\b",
    ],
    "action": [
        r"\b(I (decided|chose|implemented|built|designed|led|wrote|analyzed))\b",
        r"\b(first I|then I|next I|so I|I started by)\b",
        r"\b(I (reached out|collaborated|proposed|suggested|escalated))\b",
    ],
    "result": [
        r"\b(as a result|the outcome|we (achieved|improved|reduced|increased|shipped))\b",
        r"\b(\d+\s?%|by \d+|from \d+ to \d+|within \d+ (days|weeks|months))\b",
        r"\b(learned|takeaway|in retrospect|if I did it again)\b",
    ],
}
_STAR_WEIGHTS: dict[str, float] = {
    "situation": 0.15,
    "task":      0.15,
    "action":    0.40,
    "result":    0.30,
}

_TECHNICAL_PATTERNS: list[re.Pattern] = [
    # Mechanism explanation
    re.compile(r"\b(works by|uses|implements|under the hood|algorithm|data structure|protocol|architecture|pattern|approach)\b", re.I),
    # Tradeoff / reasoning
    re.compile(r"\b(however|tradeoff|trade-off|alternatively|because|downside|upside|advantage|disadvantage|compared to|versus|complexity)\b", re.I),
]

_SITUATIONAL_PATTERNS: list[re.Pattern] = [
    # Decision stated
    re.compile(r"\b(I would|my approach|I('d| would) (start|begin|do|handle|address|prioriti[sz]e|focus))\b", re.I),
    # Rationale given
    re.compile(r"\b(because|since|in order to|the reason|this ensures|so that|to make sure|this way)\b", re.I),
]

_SUBTYPE_PATTERNS = {
    "technical":   _TECHNICAL_PATTERNS,
    "situational": _SITUATIONAL_PATTERNS,
}


# ── Question sub-classification ──────────────────────────────────────────

_CLASSIFY_PROMPT = (
    "Classify the following interview question into exactly one category: "
    "behavioral, technical, or situational.\n\n"
    "- behavioral = asks about a past experience or accomplishment\n"
    "- technical = asks about how something works, architecture, or algorithms\n"
    "- situational = asks how you *would* handle a hypothetical scenario\n\n"
    'Respond with a single word: "behavioral", "technical", or "situational".'
)


async def classify_question_subtype(
    question_text: str,
    question_type: str,
    provider_config: Any,
) -> str:
    """
    Classify a question into ``behavioral``, ``technical``, or ``situational``.

    DSA questions are always ``technical``.  Role-specific questions are
    classified via a fast LLM call (3s timeout, fallback ``behavioral``).
    """
    if question_type == "dsa":
        return "technical"

    from .llm import call_llm

    response = await call_llm(
        messages=[
            {"role": "system", "content": _CLASSIFY_PROMPT},
            {"role": "user", "content": question_text},
        ],
        provider_config=provider_config,
        temperature=0.1,
        max_tokens=8,
        timeout_s=3.0,
    )

    if response:
        cleaned = response.strip().lower().rstrip(".")
        if cleaned in ("behavioral", "technical", "situational"):
            logger.debug("Question subtype classified: %s", cleaned)
            return cleaned

    logger.debug("Question subtype fallback: behavioral")
    return "behavioral"


# ── Coverage scoring ─────────────────────────────────────────────────────

def compute_coverage_score(transcript: str, question_subtype: str) -> float:
    """
    Score how well the transcript covers expected structural elements (0.0–1.0).

    Behavioral answers use STAR-component scoring with differential weights:
      situation 15% + task 15% + action 40% + result 30%
    This gives partial credit rather than binary 0/1 per element.

    Technical and situational use the legacy regex pattern ratio.
    """
    if question_subtype == "behavioral":
        t = transcript.lower()
        total = 0.0
        for component, raw_patterns in _BEHAVIORAL_STAR.items():
            patterns = [re.compile(p, re.I) for p in raw_patterns]
            hits = sum(1 for p in patterns if p.search(t))
            component_score = min(hits / len(patterns), 1.0)
            total += component_score * _STAR_WEIGHTS[component]
        return total

    patterns = _SUBTYPE_PATTERNS.get(question_subtype)
    if patterns is None:
        return 0.5  # unknown subtype → neutral

    if not transcript.strip():
        return 0.0

    found = sum(1 for p in patterns if p.search(transcript))
    score = found / len(patterns)
    return min(score, 1.0)
