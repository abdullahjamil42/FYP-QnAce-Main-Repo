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

_BEHAVIORAL_PATTERNS: list[re.Pattern] = [
    # Past-tense narrative
    re.compile(r"\b(I|we)\s+(did|led|built|created|managed|developed|implemented|designed|coordinated|handled|resolved|improved|reduced|increased)\b", re.I),
    # Action taken
    re.compile(r"\b(my (role|task|responsibility)|I (decided|chose|took|initiated|proposed|recommended))\b", re.I),
    # Outcome / result
    re.compile(r"\b(result(ed)?|outcome|impact|improved|reduced|increased|saved|achieved|delivered|led to|grew|raised)\b", re.I),
]

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
    "behavioral": _BEHAVIORAL_PATTERNS,
    "technical": _TECHNICAL_PATTERNS,
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
    Score how well the transcript covers expected structural elements.

    Returns a float 0.0-1.0 = ``elements_found / elements_expected``,
    capped at 1.0.
    """
    patterns = _SUBTYPE_PATTERNS.get(question_subtype)
    if patterns is None:
        return 0.5  # unknown subtype → neutral

    if not transcript.strip():
        return 0.0

    found = sum(1 for p in patterns if p.search(transcript))
    score = found / len(patterns)
    return min(score, 1.0)
