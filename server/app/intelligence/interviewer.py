"""Q&Ace interviewer intelligence: two-stage classify-then-generate flow."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from .llm import LLMProviderConfig, resolve_provider_config, stream_llm

logger = logging.getLogger("qace.interviewer")

MODES = {
    "ADVANCE",
    "PROBE_DEPTH",
    "PROBE_GAP",
    "REDIRECT",
    "CHALLENGE",
    "RESCUE",
    "INTERRUPT",
    "CONFRONT",
    "ACKNOWLEDGE_IDK",
    "REFRAME",
    "SKEPTIC",
    "BULLDOZE",
    "MEMORY_PRESS",
    "PRESSURE_CLOCK",
    "DEAD_SILENCE",
    "CV_VERIFY",
    "ACHIEVEMENT_PROBE",
    "CAREER_PROBE",
}

ALLOWED_FLAGS = {"contradiction", "overclaim", "bluff", "hint-seeking", "hostile"}

STOPWORDS = {
    "the", "a", "an", "to", "of", "in", "on", "for", "with", "is", "are", "was", "were",
    "and", "or", "that", "this", "it", "as", "at", "by", "from", "be", "have", "has", "had",
}

TECH_TERMS = {
    "api", "rest", "graphql", "microservice", "microservices", "kafka", "redis", "postgres", "mysql",
    "mongodb", "kubernetes", "docker", "lambda", "queue", "cache", "caching", "load", "balancer",
    "gateway", "python", "java", "golang", "typescript", "react", "node", "flask", "fastapi",
    "django", "terraform", "ansible", "spark", "airflow", "pytorch", "onnx",
}

BUZZWORDS = {
    "synergy", "blockchain", "quantum", "ai-powered", "decentralized", "web3", "kubernetes",
    "microservices", "serverless", "disruptive", "cutting-edge", "next-gen",
}

IDK_PATTERNS = [
    re.compile(r"\bi\s+do\s*not\s+know\b", re.IGNORECASE),
    re.compile(r"\bi\s+don'?t\s+know\b", re.IGNORECASE),
    re.compile(r"\bnot\s+sure\b", re.IGNORECASE),
    re.compile(r"\bno\s+idea\b", re.IGNORECASE),
]

CLARIFICATION_PATTERNS = [
    re.compile(r"\bcan\s+you\s+clarify\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+do\s+you\s+mean\b", re.IGNORECASE),
    re.compile(r"\bdo\s+you\s+mean\b", re.IGNORECASE),
    re.compile(r"\bwhich\s+part\b", re.IGNORECASE),
]

HINT_PATTERNS = [
    re.compile(r"\bhint\b", re.IGNORECASE),
    re.compile(r"\bon\s+the\s+right\s+track\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+are\s+you\s+looking\s+for\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+do\s+you\s+want\b", re.IGNORECASE),
    re.compile(r"\bany\s+clue\b", re.IGNORECASE),
]

HOSTILE_PATTERNS = [
    re.compile(r"\bthis\s+question\s+is\s+stupid\b", re.IGNORECASE),
    re.compile(r"\bthat\s+is\s+stupid\b", re.IGNORECASE),
    re.compile(r"\bwhatever\b", re.IGNORECASE),
    re.compile(r"\bthis\s+is\s+dumb\b", re.IGNORECASE),
]


@dataclass
class LLMCallResult:
    text: str
    ttft_ms: float
    total_ms: float


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9\-]+", (text or "").lower())


def _token_set(text: str) -> set[str]:
    return {t for t in _tokenize(text) if t not in STOPWORDS and len(t) > 1}


def _jaccard(a: str, b: str) -> float:
    sa = _token_set(a)
    sb = _token_set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / max(union, 1)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _state_default() -> dict[str, Any]:
    return {
        "key_claims": [],
        "question_stats": {},
        "idk_count": 0,
        "interrupt_count": 0,
        "last_modes": [],
        "flags_history": [],
        "turn_history": [],
        "session_summary": "",
    }


def _ensure_state(state: Optional[dict[str, Any]]) -> dict[str, Any]:
    merged = _state_default()
    if isinstance(state, dict):
        merged.update(state)
    for key, default in _state_default().items():
        if key not in merged or not isinstance(merged[key], type(default)):
            merged[key] = default
    return merged


def _question_key(question: str) -> str:
    q = _normalize_text(question).lower()
    if len(q) > 220:
        q = q[:220]
    return q


def _estimate_rag_relevance(rag_distances: list[float]) -> float:
    vals: list[float] = []
    for d in rag_distances or []:
        try:
            vals.append(float(d))
        except Exception:
            pass
    if not vals:
        return 0.0
    # Chroma distance is lower-is-better; map to [0,1].
    best = min(vals)
    return _clamp(1.0 / (1.0 + max(best, 0.0)), 0.0, 1.0)


def _extract_numbers(text: str) -> list[str]:
    return re.findall(r"\b\d+(?:\.\d+)?%?\b", text)


def _sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+", _normalize_text(text))
    return [s.strip() for s in raw if s.strip()]


def _detect_topic(text: str) -> str:
    tokens = _tokenize(text)
    for token in tokens:
        if token in TECH_TERMS:
            return token
    return " ".join(tokens[:4])


def _extract_claims(answer: str, question: str, turn_index: int) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for sentence in _sentences(answer):
        low = sentence.lower()
        has_metric = bool(_extract_numbers(sentence))
        has_tech = any(term in low for term in TECH_TERMS)
        has_ownership = bool(re.search(r"\b(i|my|mine|personally|i\s+led|i\s+built|i\s+decided|i\s+owned)\b", low))
        if not (has_metric or has_tech or has_ownership):
            continue
        polarity = "neg" if re.search(r"\b(not|never|didn't|did not|no)\b", low) else "pos"
        claims.append(
            {
                "text": sentence,
                "topic": _detect_topic(sentence),
                "question": _normalize_text(question),
                "turn_index": int(turn_index),
                "numbers": _extract_numbers(sentence),
                "polarity": polarity,
            }
        )
    return claims


def _find_contradiction(new_claims: list[dict[str, Any]], existing_claims: list[dict[str, Any]]) -> Optional[str]:
    for new_claim in new_claims:
        for old_claim in reversed(existing_claims):
            same_topic = _jaccard(new_claim.get("topic", ""), old_claim.get("topic", "")) >= 0.5
            similar_claim = _jaccard(new_claim.get("text", ""), old_claim.get("text", "")) >= 0.35
            if not (same_topic or similar_claim):
                continue

            old_nums = set(old_claim.get("numbers", []))
            new_nums = set(new_claim.get("numbers", []))
            numeric_conflict = bool(old_nums and new_nums and old_nums.isdisjoint(new_nums))
            polarity_conflict = old_claim.get("polarity") != new_claim.get("polarity")

            if numeric_conflict or polarity_conflict:
                return (
                    f"Earlier you said '{old_claim.get('text', '')}'. "
                    f"Now you said '{new_claim.get('text', '')}'."
                )
    return None


def _detect_overclaim(answer: str) -> bool:
    low = answer.lower()
    team_refs = len(re.findall(r"\b(we|our|us|team)\b", low))
    first_refs = len(re.findall(r"\b(i|me|my|mine)\b", low))
    has_decision = bool(re.search(r"\b(decided|chose|implemented|built|owned|drove|changed|designed)\b", low))
    has_personal_impact = bool(re.search(r"\bi\b[^.?!]{0,60}\b\d+(?:\.\d+)?%?\b", low))
    return team_refs > first_refs and not has_decision and not has_personal_impact


def _detect_bluff(answer: str, vocal_confidence: float, text_quality_score: float, rag_relevance: float) -> bool:
    tokens = _tokenize(answer)
    if not tokens:
        return False
    buzz_count = sum(1 for t in tokens if t in BUZZWORDS)
    density = buzz_count / max(len(tokens), 1)
    return vocal_confidence >= 0.75 and text_quality_score <= 55.0 and rag_relevance <= 0.35 and (
        density >= 0.06 or buzz_count >= 4
    )


def _detect_hint_seeking(answer: str) -> bool:
    return any(p.search(answer or "") for p in HINT_PATTERNS)


def _detect_hostile(answer: str) -> bool:
    return any(p.search(answer or "") for p in HOSTILE_PATTERNS)


def _detect_idk(answer: str) -> bool:
    return any(p.search(answer or "") for p in IDK_PATTERNS)


def _detect_reframe(answer: str) -> bool:
    return any(p.search(answer or "") for p in CLARIFICATION_PATTERNS)


def _question_stats(state: dict[str, Any], question: str) -> dict[str, int]:
    key = _question_key(question)
    stats = state["question_stats"].get(key)
    if not isinstance(stats, dict):
        stats = {"probes": 0, "redirects": 0}
        state["question_stats"][key] = stats
    stats.setdefault("probes", 0)
    stats.setdefault("redirects", 0)
    return stats


def _last_n_turns(history: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    if n <= 0:
        return []
    trimmed = history[-n:]
    out: list[dict[str, Any]] = []
    for item in trimmed:
        out.append(
            {
                "question": _normalize_text(str(item.get("question", "")))[:220],
                "answer": _normalize_text(str(item.get("answer", "")))[:320],
                "mode": str(item.get("mode", "")),
                "flags": list(item.get("flags", []))[:5],
            }
        )
    return out


def _compress_session_summary(history: list[dict[str, Any]], max_chars: int) -> str:
    lines: list[str] = []
    for item in history[-10:]:
        q = _normalize_text(str(item.get("question", "")))
        a = _normalize_text(str(item.get("answer", "")))
        mode = str(item.get("mode", ""))
        if len(q) > 80:
            q = q[:80].rstrip() + "..."
        if len(a) > 120:
            a = a[:120].rstrip() + "..."
        lines.append(f"Q:{q} | A:{a} | Mode:{mode}")

    summary = "\n".join(lines)
    if len(summary) > max_chars:
        summary = summary[-max_chars:]
    return summary


def _drain_completed_sentences(buffer: str) -> tuple[list[str], str]:
    """Split complete sentence chunks from a streaming token buffer."""
    completed: list[str] = []
    remaining = buffer
    while True:
        match = re.search(r"[.!?](?=\s|$)", remaining)
        if match is None:
            break
        end = match.end()
        chunk = _normalize_text(remaining[:end])
        remaining = remaining[end:].lstrip()
        if chunk:
            completed.append(chunk)
    return completed, remaining


def _override_model(provider: LLMProviderConfig, model_name: str) -> LLMProviderConfig:
    override = (model_name or "").strip()
    if provider.provider == "local":
        if override and os.path.exists(override):
            model = override
        else:
            model = provider.model
    else:
        model = override or provider.model
    return LLMProviderConfig(provider=provider.provider, api_key=provider.api_key, model=model)


async def _collect_stream(
    transcript: str,
    system_prompt: str,
    provider_config: LLMProviderConfig,
    temperature: float,
    max_tokens: int,
) -> LLMCallResult:
    t0 = time.perf_counter()
    ttft = 0.0
    tokens: list[str] = []
    async for token in stream_llm(
        transcript,
        system_prompt,
        provider_config,
        temperature=temperature,
        max_tokens=max_tokens,
    ):
        if not tokens:
            ttft = (time.perf_counter() - t0) * 1000.0
        tokens.append(token)
    total = (time.perf_counter() - t0) * 1000.0
    return LLMCallResult(text="".join(tokens).strip(), ttft_ms=round(ttft, 1), total_ms=round(total, 1))


def _classifier_system_prompt(stage: str = "", stress_level: str = "none") -> str:
    base = (
        "You are an interview mode classifier. Return JSON only with no prose. "
        "Allowed modes: ADVANCE, PROBE_DEPTH, PROBE_GAP, REDIRECT, CHALLENGE, RESCUE, "
        "INTERRUPT, CONFRONT, ACKNOWLEDGE_IDK, REFRAME, ENCOURAGE, CLARIFY, WRAP_UP, HYPOTHETICAL, "
        "SKEPTIC, BULLDOZE, MEMORY_PRESS, PRESSURE_CLOCK, DEAD_SILENCE, CV_VERIFY, ACHIEVEMENT_PROBE, CAREER_PROBE. "
        "Output schema: {\"mode\": string, \"evidence\": string, \"follow_up_anchor\": string, "
        "\"active_flags\": [string]}. "
        "Use only active_flags from: contradiction, overclaim, bluff, hint-seeking, hostile. "
        "Evidence must be one sentence. Follow_up_anchor must be a concrete phrase from candidate text. "
        "Never output markdown. Never output anything other than a single valid JSON object."
    )
    if stage == "WRAP_UP":
        base += " CRITICAL: The interview is in the WRAP_UP stage. Strongly bias your classification toward the WRAP_UP mode."
        
    if stress_level in ("high", "brutal"):
        base += " CRITICAL: Stress level is high. Bias toward SKEPTIC, BULLDOZE, MEMORY_PRESS, and CHALLENGE."
    return base


def _parse_classifier_output(text: str) -> Optional[dict[str, Any]]:
    payload: Any = None
    raw = (text or "").strip()
    if not raw:
        return None

    try:
        payload = json.loads(raw)
    except Exception:
        first = raw.find("{")
        last = raw.rfind("}")
        if first >= 0 and last > first:
            try:
                payload = json.loads(raw[first:last + 1])
            except Exception:
                return None
        else:
            return None

    if not isinstance(payload, dict):
        return None

    mode = str(payload.get("mode", "")).strip().upper()
    if mode not in MODES:
        return None

    evidence = _normalize_text(str(payload.get("evidence", "")))
    anchor = _normalize_text(str(payload.get("follow_up_anchor", "")))
    flags_raw = payload.get("active_flags", [])
    if not isinstance(flags_raw, list):
        flags_raw = []
    flags: list[str] = []
    for item in flags_raw:
        s = str(item).strip().lower()
        if s in ALLOWED_FLAGS and s not in flags:
            flags.append(s)

    return {
        "mode": mode,
        "evidence": evidence[:240],
        "follow_up_anchor": anchor[:200],
        "active_flags": flags,
    }


def _build_stress_tone_prompt(stress_level: str) -> str:
    if stress_level == "mild":
        return "Tone is professional but demanding. Do not use affirmations or reflexive praise. Keep follow-ups dry and direct. "
    elif stress_level == "high":
        return "Tone is curt and confrontational. Provide no acknowledgments. Use phrases like 'Bottom line?' or 'Get to the point.'. "
    elif stress_level == "brutal":
        return "Tone is relentlessly skeptical, cold, and challenging. Dismiss unquantified claims immediately. "
    else:
        return "Tone is warm, direct, curious, and professional. "

def _build_mode_prompt(mode: str, redirect_count: int, active_flags: list[str], stress_level: str = "none") -> str:
    tone = _build_stress_tone_prompt(stress_level)
    if mode == "CHALLENGE" or "bluff" in active_flags:
        tone = "Tone is firm, forensic, and skeptical. "
    elif mode == "ENCOURAGE":
        tone = "Tone is exceptionally warm, patient, and supportive. "
    elif mode == "WRAP_UP":
        tone = "Tone is gracious, conclusive, and highly welcoming. "
        
    base = (
        f"You are a senior interviewer at a competitive software company. {tone}"
        "Do not use bullet points, headers, or lists. "
        "Do not say great answer, interesting, absolutely, or reflexive praise. "
        "Do not reveal rubric or ideal answer. "
        "Always respond in 2 to 3 spoken sentences optimized for TTS."
    )

    mode_directives = {
        "ADVANCE": (
            "Acknowledge briefly in one clause, then use a transition phrase like 'Moving on to...' or 'Let's switch gears...' before the next question. "
            "Keep momentum and avoid over-praise."
        ),
        "PROBE_DEPTH": (
            "Answer is surface-level but directionally correct. "
            "Anchor on a concrete phrase the candidate used and probe one level deeper. "
            "Do not ask generic tell me more questions."
        ),
        "PROBE_GAP": (
            "Acknowledge the part that is correct without implying completeness. "
            "Probe the missing dimension with curiosity, not correction."
        ),
        "REDIRECT": (
            "Answer is off-topic. "
            "If this is first redirect, briefly acknowledge and gently steer back with let's bring it back to. "
            "If this is second or more redirect, restate the question near-verbatim with no softening."
        ),
        "CHALLENGE": (
            "Candidate may be bluffing or overclaiming. "
            "Ask for one concrete decision, number, or measurable outcome they personally owned. "
            "Force specifics that cannot be answered in generalities."
        ),
        "RESCUE": (
            "Candidate appears stuck. Offer a simpler starting angle without giving away the answer. "
            "Ask them to begin with what they do know."
        ),
        "INTERRUPT": (
            "Candidate has over-talked. Wait for a natural breath, acknowledge you heard them, "
            "then pivot with a focused question anchored to a phrase from the second half of their response."
        ),
        "CONFRONT": (
            "Surface the contradiction directly but non-accusatorily. Quote both claims briefly and invite reconciliation."
        ),
        "ACKNOWLEDGE_IDK": (
            "Candidate calmly admitted not knowing. Acknowledge briefly, then move to next question or adjacent angle."
        ),
        "REFRAME": (
            "Candidate asked for clarification. Clarify the ambiguity directly without repeating the whole question, "
            "then invite their answer."
        ),
        "ENCOURAGE": (
            "Candidate seems hesitant or lacks confidence. "
            "Validate their thought process and provide a gentle, supportive nudge to keep going."
        ),
        "CLARIFY": (
            "Candidate gave a disorganized or confusing answer. "
            "Ask them to explain a specific piece of their logic again more simply."
        ),
        "WRAP_UP": (
            "The technical portion of the interview is concluding. "
            "Provide a warm closing statement acknowledging their effort, and ask if they have any questions for you."
        ),
        "HYPOTHETICAL": (
            "Shift the current topic into a new 'what-if' hypothetical scenario to test adaptability. "
            "Keep the scenario realistic to the current topic."
        ),
        "SKEPTIC": (
            "Pick one concrete claim the candidate made and challenge it directly. Express doubt about its effectiveness."
        ),
        "BULLDOZE": (
            "Cut the candidate off. Start with 'Let me stop you there.' and force them to answer a very narrow question."
        ),
        "MEMORY_PRESS": (
            "Reference something they said 2-4 turns ago. Challenge them on whether their current answer is consistent with it."
        ),
        "PRESSURE_CLOCK": (
            "Create a fake time constraint. Say 'We are running out of time, I need the short answer' and ask a tough question."
        ),
        "DEAD_SILENCE": (
            "Do not output spoken text. This mode represents intentional silence. The frontend will handle the silence delay."
        ),
        "CV_VERIFY": (
            "Reference their CV explicitly. Ask them to reconcile a discrepancy between what they just said and their resume."
        ),
        "ACHIEVEMENT_PROBE": (
            "Drill aggressively into a specific metric or achievement listed on their CV context. Ask how they achieved that exact number."
        ),
        "CAREER_PROBE": (
            "Ask a probing, potentially uncomfortable question about their career transitions, gaps, or motivations based on the CV."
        ),
    }

    extra: list[str] = []
    if mode == "REDIRECT":
        if redirect_count <= 1:
            extra.append("This is first redirect for this question.")
        else:
            extra.append("This is second-or-later redirect for this question.")

    if "overclaim" in active_flags and mode == "CHALLENGE":
        extra.append(
            "Overclaim flag is active. Ask explicitly what they personally decided, built, or changed using first-person framing."
        )

    if "bluff" in active_flags and mode == "CHALLENGE":
        extra.append(
            "Bluff flag is active. Ask for a real situation and concrete outcome, not a definition or theory."
        )

    if "hint-seeking" in active_flags:
        extra.append(
            "If candidate asks for hints, decline giving answers directly but provide a useful angle or dimension to think through."
        )

    if "hostile" in active_flags:
        extra.append("Keep tone calm and professional. De-escalate without sounding submissive.")

    directive = mode_directives.get(mode, mode_directives["PROBE_GAP"])
    full = base + " " + directive
    if extra:
        full += " " + " ".join(extra)
    return full


def _fallback_classification(
    transcript: str,
    current_question: str,
    rag_relevance: float,
    vocal_confidence: float,
    text_quality_score: float,
    active_flags: list[str],
    monologue_flag: bool,
    stress_level: str = "none",
) -> dict[str, Any]:
    answer = _normalize_text(transcript)
    evidence = "Selected via deterministic fallback logic."
    anchor = ""

    if answer:
        chunks = _sentences(answer)
        if chunks:
            anchor = chunks[-1][:120]
        else:
            anchor = answer[:120]

    if monologue_flag:
        return {
            "mode": "BULLDOZE" if stress_level in ("high", "brutal") else "INTERRUPT",
            "evidence": "Candidate produced a long monologue with low turn efficiency.",
            "follow_up_anchor": anchor,
            "active_flags": active_flags,
        }

    if "contradiction" in active_flags:
        mode = "CONFRONT"
    elif _detect_reframe(answer):
        mode = "REFRAME"
    elif _detect_idk(answer):
        mode = "ACKNOWLEDGE_IDK" if vocal_confidence >= 0.55 else "RESCUE"
    elif rag_relevance < 0.20 and _jaccard(answer, current_question) < 0.18:
        mode = "REDIRECT"
    elif "bluff" in active_flags:
        mode = "CHALLENGE"
    elif text_quality_score >= 78.0 and rag_relevance >= 0.45:
        mode = "SKEPTIC" if stress_level in ("high", "brutal") else "ADVANCE"
    elif text_quality_score >= 60.0:
        mode = "PROBE_DEPTH"
    else:
        mode = "PROBE_GAP"

    return {
        "mode": mode,
        "evidence": evidence,
        "follow_up_anchor": anchor,
        "active_flags": active_flags,
    }


def _fallback_spoken(
    mode: str,
    next_question: str,
    follow_up_anchor: str,
    contradiction_evidence: str,
    redirect_count: int,
    active_flags: list[str],
) -> str:
    anchor = follow_up_anchor or "that point"

    if mode == "ADVANCE":
        return f"Okay, good. Let us move forward. {next_question}"
    if mode == "PROBE_DEPTH":
        return f"Right, I heard your point about {anchor}. Walk me one level deeper into how you executed that decision."
    if mode == "PROBE_GAP":
        return f"You covered part of it, and that helps. What about {anchor} was most critical when this was under real pressure?"
    if mode == "REDIRECT":
        if redirect_count <= 1:
            return f"I hear you. Let us bring it back to the question. {next_question}"
        return next_question
    if mode == "CHALLENGE":
        if "overclaim" in active_flags:
            return "Be specific about your personal role. What exact decision did you make yourself, and what measurable result changed because of your decision?"
        return "Give me one concrete example from real work, including a specific decision and measurable outcome."
    if mode == "RESCUE":
        return "That is okay. Start with the first part you are confident about, then we can build from there. What do you know for sure about this problem?"
    if mode == "INTERRUPT":
        return f"I am going to pause you there for time. I heard your point about {anchor}. What is the single most important takeaway in one sentence?"
    if mode == "CONFRONT":
        return f"I want to reconcile something before we continue. {contradiction_evidence} Can you clarify which version is accurate?"
    if mode == "ACKNOWLEDGE_IDK":
        return f"Understood. Let us keep momentum with a related angle. {next_question}"
    if mode == "REFRAME":
        return "Good question. Focus on the concrete decisions and trade-offs you made, not generic theory. Can you answer it from that angle?"
    if mode == "ENCOURAGE":
        return "You're on the right track. Keep going with that thought."
    if mode == "CLARIFY":
        return "Could you break that down a bit more simply for me?"
    if mode == "WRAP_UP":
        return "Got it. That concludes the technical portion of our interview. Do you have any questions for me?"
    if mode == "HYPOTHETICAL":
        return f"Interesting. What if the situation was slightly different? {next_question}"
    if mode == "SKEPTIC":
        return f"I'm not entirely convinced by that. How exactly did '{anchor}' move the needle?"
    if mode == "BULLDOZE":
        return f"Let me stop you right there. What is the bottom line on {anchor}?"
    if mode == "MEMORY_PRESS":
        return f"Wait, earlier you said something else. Does this new answer about {anchor} still hold up?"
    if mode == "PRESSURE_CLOCK":
        return f"We have very little time left. Give me a short answer on {anchor}."
    if mode == "DEAD_SILENCE":
        return ""
    if mode == "CV_VERIFY":
        return "Your CV says something slightly different. Can you clarify?"
    if mode == "ACHIEVEMENT_PROBE":
        return "You listed a strong metric on your resume. How exactly did you achieve it?"
    if mode == "CAREER_PROBE":
        return "Looking at your work history, what was the real reason behind that transition?"
    return next_question

async def classify_interviewer_turn(
    *,
    transcript: str,
    current_question: str,
    conversation_history: list[dict[str, Any]] | None,
    previous_mode: str,
    session_state: Optional[dict[str, Any]],
    monologue_flag: bool,
    settings: Any,
    stage: str = "",
    stress_level: str = "none",
) -> dict[str, Any]:
    """Run classifier call (mode selection) only, decoupled from heavy perception/extraction."""
    state = _ensure_state(session_state)
    history = list(conversation_history or state.get("turn_history", []))
    history_window = max(1, int(getattr(settings, "interviewer_history_window", 3)))

    active_flags: list[str] = []
    # Seed flags based on transcript alone (without scoring)
    if _detect_overclaim(transcript):
        active_flags.append("overclaim")
    if _detect_hint_seeking(transcript):
        active_flags.append("hint-seeking")
    if _detect_hostile(transcript):
        active_flags.append("hostile")

    provider = resolve_provider_config(settings)
    classifier_result: Optional[dict[str, Any]] = None
    classifier_ms = 0.0
    classifier_ttft_ms = 0.0

    recent_turns = _last_n_turns(history, history_window)
    previous_mode_norm = (previous_mode or "").strip().upper()
    if previous_mode_norm not in MODES and state.get("last_modes"):
        previous_mode_norm = str(state["last_modes"][-1]).upper()

    classifier_payload = {
        "candidate_transcript": _normalize_text(transcript),
        "current_question": _normalize_text(current_question),
        "recent_turns": recent_turns,
        "previous_mode": previous_mode_norm,
        "seed_flags": active_flags,
    }

    if provider is not None:
        try:
            cls_model = getattr(settings, "interviewer_classifier_model", "")
            cls_cfg = _override_model(provider, cls_model)
            cls_temp = _safe_float(getattr(settings, "interviewer_classifier_temperature", 0.0), 0.0)
            cls_tokens = int(getattr(settings, "interviewer_classifier_max_tokens", 150))
            cls_call = await _collect_stream(
                json.dumps(classifier_payload, ensure_ascii=True),
                _classifier_system_prompt(stage, stress_level),
                cls_cfg,
                temperature=_clamp(cls_temp, 0.0, 1.0),
                max_tokens=max(80, cls_tokens),
            )
            classifier_result = _parse_classifier_output(cls_call.text)
            classifier_ms = cls_call.total_ms
            classifier_ttft_ms = cls_call.ttft_ms
        except Exception as exc:
            logger.warning("Classifier call failed: %s", exc)

    if classifier_result is None:
        # Pass dummy values for perception-based fallback triggers (RAG relevance, confidence)
        classifier_result = _fallback_classification(
            transcript=transcript,
            current_question=current_question,
            rag_relevance=0.0,
            vocal_confidence=0.5,
            text_quality_score=60.0,
            active_flags=active_flags,
            monologue_flag=monologue_flag,
            stress_level=stress_level,
        )

    mode = str(classifier_result.get("mode", "PROBE_GAP")).upper()
    evidence = _normalize_text(str(classifier_result.get("evidence", ""))) or "Mode selected by policy."
    follow_up_anchor = _normalize_text(str(classifier_result.get("follow_up_anchor", "")))
    cls_flags = [f for f in classifier_result.get("active_flags", []) if f in ALLOWED_FLAGS]
    for f in active_flags:
        if f not in cls_flags:
            cls_flags.append(f)

    # Hard safety overrides
    if monologue_flag:
        mode = "INTERRUPT"

    return {
        "mode": mode,
        "evidence": evidence,
        "follow_up_anchor": follow_up_anchor,
        "active_flags": cls_flags,
        "classifier_ms": round(classifier_ms, 1),
        "classifier_ttft_ms": round(classifier_ttft_ms, 1),
    }


async def generate_interviewer_response(
    *,
    transcript: str,
    current_question: str,
    classifier_result: dict[str, Any],
    ideal_answer_rubric: str,
    rag_passages: list[str],
    rag_distances: list[float],
    vocal_confidence: float,
    text_quality_score: float,
    text_quality_label: str,
    conversation_history: list[dict[str, Any]] | None,
    session_state: Optional[dict[str, Any]],
    next_question: str,
    settings: Any,
    on_generator_sentence_chunk: Optional[Callable[[str], Awaitable[None]]] = None,
    stress_level: str = "none",
    cv_context: str = "",
) -> dict[str, Any]:
    """Run generator call using pre-selected mode and full perception data."""
    state = _ensure_state(session_state)
    history = list(conversation_history or state.get("turn_history", []))
    history_window = max(1, int(getattr(settings, "interviewer_history_window", 3)))
    summary_max_chars = max(300, int(getattr(settings, "interviewer_summary_max_chars", 1200)))
    
    q_stats = _question_stats(state, current_question)
    rag_relevance = _estimate_rag_relevance(rag_distances)
    
    turn_index = len(history) + 1
    new_claims = _extract_claims(transcript, current_question, turn_index)
    contradiction_evidence = _find_contradiction(new_claims, state.get("key_claims", []))

    mode = classifier_result["mode"]
    evidence = classifier_result["evidence"]
    follow_up_anchor = classifier_result["follow_up_anchor"]
    cls_flags = classifier_result["active_flags"]

    # Late addition of contradiction flag if perception/RAG find it
    if contradiction_evidence:
        if "contradiction" not in cls_flags:
            cls_flags.append("contradiction")
        mode = "CONFRONT"

    redirect_count = int(q_stats.get("redirects", 0)) + (1 if mode == "REDIRECT" else 0)
    if mode == "REDIRECT":
        q_stats["redirects"] = int(q_stats.get("redirects", 0)) + 1
    if mode in {"PROBE_DEPTH", "PROBE_GAP", "CHALLENGE"}:
        q_stats["probes"] = int(q_stats.get("probes", 0)) + 1
    if mode in {"RESCUE", "ACKNOWLEDGE_IDK"} and _detect_idk(transcript):
        state["idk_count"] = int(state.get("idk_count", 0)) + 1
    if mode == "INTERRUPT":
        state["interrupt_count"] = int(state.get("interrupt_count", 0)) + 1

    session_summary = state.get("session_summary", "")
    if not session_summary:
        session_summary = _compress_session_summary(history, summary_max_chars)

    generator_prompt = _build_mode_prompt(mode, redirect_count, cls_flags, stress_level=stress_level)
    recent_turns = _last_n_turns(history, history_window)
    
    generator_payload = {
        "mode": mode,
        "evidence": evidence,
        "follow_up_anchor": follow_up_anchor,
        "active_flags": cls_flags,
        "current_question": _normalize_text(current_question),
        "next_question": _normalize_text(next_question),
        "candidate_transcript": _normalize_text(transcript),
        "ideal_answer_rubric": _normalize_text(ideal_answer_rubric)[:1200],
        "rag_relevance": round(rag_relevance, 3),
        "rag_passages": [
            _normalize_text(p)[:240] for p in (rag_passages or [])[:3]
        ],
        "vocal_confidence": round(_clamp(vocal_confidence, 0.0, 1.0), 3),
        "text_quality_score": round(_clamp(text_quality_score, 0.0, 100.0), 1),
        "text_quality_label": _normalize_text(text_quality_label),
        "recent_turns": recent_turns,
        "session_summary": session_summary,
        "redirect_count_for_question": redirect_count,
        "idk_count": int(state.get("idk_count", 0)),
        "interrupt_count": int(state.get("interrupt_count", 0)),
    }
    
    if cv_context:
        generator_payload["cv_context"] = cv_context

    spoken_response = ""
    generator_ttft_ms = 0.0
    generator_ms = 0.0
    streamed_chunk_count = 0
    provider = resolve_provider_config(settings)

    if provider is not None:
        try:
            gen_model = getattr(settings, "interviewer_generator_model", "")
            gen_cfg = _override_model(provider, gen_model)
            t_gen_start = time.perf_counter()
            tokens: list[str] = []
            pending = ""
            emitted_sentences: list[str] = []
            sentence_limit = 3
            async for token in stream_llm(
                json.dumps(generator_payload, ensure_ascii=True),
                generator_prompt,
                gen_cfg,
                temperature=0.55,
                max_tokens=max(80, int(getattr(settings, "llm_max_tokens", 120))),
            ):
                if not tokens:
                    generator_ttft_ms = (time.perf_counter() - t_gen_start) * 1000.0
                tokens.append(token)
                pending += token

                completed, pending = _drain_completed_sentences(pending)
                for sentence in completed:
                    emitted_sentences.append(sentence)
                    if on_generator_sentence_chunk is not None:
                        try:
                            await on_generator_sentence_chunk(sentence)
                            streamed_chunk_count += 1
                        except Exception as exc:
                            logger.warning("Generator chunk callback failed (%s)", exc)
                    if len(emitted_sentences) >= sentence_limit:
                        break
                if len(emitted_sentences) >= sentence_limit:
                    break

            if pending.strip() and len(emitted_sentences) < sentence_limit:
                tail = _normalize_text(pending)
                if tail:
                    emitted_sentences.append(tail)
                    if on_generator_sentence_chunk is not None:
                        try:
                            await on_generator_sentence_chunk(tail)
                            streamed_chunk_count += 1
                        except Exception as exc:
                            logger.warning("Generator tail callback failed (%s)", exc)

            spoken_response = _normalize_text(" ".join(emitted_sentences))
            if not spoken_response:
                spoken_response = _normalize_text("".join(tokens))

            generator_ms = (time.perf_counter() - t_gen_start) * 1000.0
        except Exception as exc:
            logger.warning("Generator call failed: %s", exc)

    if not spoken_response:
        spoken_response = _fallback_spoken(
            mode=mode,
            next_question=next_question,
            follow_up_anchor=follow_up_anchor,
            contradiction_evidence=contradiction_evidence or evidence,
            redirect_count=redirect_count,
            active_flags=cls_flags,
        )
        if on_generator_sentence_chunk is not None:
            try:
                await on_generator_sentence_chunk(spoken_response)
                streamed_chunk_count += 1
            except Exception as exc:
                logger.warning("Fallback chunk callback failed (%s)", exc)

    spoken_response = re.sub(r"\s+", " ", spoken_response).strip()
    spoken_response = spoken_response.replace(":", "")

    turn_record = {
        "question": _normalize_text(current_question),
        "answer": _normalize_text(transcript),
        "mode": mode,
        "flags": cls_flags,
        "evidence": evidence,
        "anchor": follow_up_anchor,
    }
    history.append(turn_record)

    state["turn_history"] = history[-50:]
    state["key_claims"] = (state.get("key_claims", []) + new_claims)[-200:]
    state["last_modes"] = (state.get("last_modes", []) + [mode])[-12:]
    state["flags_history"] = (state.get("flags_history", []) + cls_flags)[-200:]
    state["session_summary"] = _compress_session_summary(state["turn_history"], summary_max_chars)

    return {
        "spoken_response": spoken_response,
        "mode": mode,
        "evidence": evidence,
        "follow_up_anchor": follow_up_anchor,
        "active_flags": cls_flags,
        "state": state,
        "history": state["turn_history"],
        "generator_ms": round(generator_ms, 1),
        "llm_ttft_ms": round(generator_ttft_ms, 1),
        "streamed_chunk_count": streamed_chunk_count,
        "rag_relevance": round(rag_relevance, 3),
        "classifier_ms": round(classifier_result.get("classifier_ms", 0.0), 1),
        "classifier_ttft_ms": round(classifier_result.get("classifier_ttft_ms", 0.0), 1),
    }


async def generate_interviewer_turn(
    *,
    transcript: str,
    current_question: str,
    ideal_answer_rubric: str,
    rag_passages: list[str],
    rag_distances: list[float],
    vocal_confidence: float,
    text_quality_score: float,
    text_quality_label: str,
    conversation_history: list[dict[str, Any]] | None,
    previous_mode: str,
    session_state: Optional[dict[str, Any]],
    monologue_flag: bool,
    next_question: str,
    settings: Any,
    stage: str = "",
    on_generator_sentence_chunk: Optional[Callable[[str], Awaitable[None]]] = None,
    stress_level: str = "none",
    cv_context: str = "",
) -> dict[str, Any]:
    """Backward compatibility wrapper: runs classify then generate sequentially."""
    classifier_result = await classify_interviewer_turn(
        transcript=transcript,
        current_question=current_question,
        conversation_history=conversation_history,
        previous_mode=previous_mode,
        session_state=session_state,
        monologue_flag=monologue_flag,
        settings=settings,
        stage=stage,
        stress_level=stress_level,
    )
    return await generate_interviewer_response(
        transcript=transcript,
        current_question=current_question,
        classifier_result=classifier_result,
        ideal_answer_rubric=ideal_answer_rubric,
        rag_passages=rag_passages,
        rag_distances=rag_distances,
        vocal_confidence=vocal_confidence,
        text_quality_score=text_quality_score,
        text_quality_label=text_quality_label,
        conversation_history=conversation_history,
        session_state=session_state,
        next_question=next_question,
        settings=settings,
        on_generator_sentence_chunk=on_generator_sentence_chunk,
        stress_level=stress_level,
        cv_context=cv_context,
    )


async def generate_small_talk_opener(settings: Any) -> str:
    """Generate a natural, short small talk opener using the LLM."""
    default_opener = "Hi there. Thanks for joining. How is your day going so far?"
    provider = resolve_provider_config(settings)
    if not provider:
        return default_opener

    system_prompt = (
        "You are an AI interviewer starting a session. Generate a single, short, warm small-talk opening. "
        "For example, ask how their day is going or thank them for making time. "
        "Maximum 2 sentences. No lists, no headers, be conversational and natural."
    )
    try:
        gen_model = getattr(settings, "interviewer_generator_model", "")
        gen_cfg = _override_model(provider, gen_model)
        
        call_res = await _collect_stream(
            transcript="Start the interview.",
            system_prompt=system_prompt,
            provider_config=gen_cfg,
            temperature=0.7,
            max_tokens=50,
        )
        if call_res.text:
            return call_res.text
    except Exception as exc:
        logger.warning("Failed to generate small talk opener: %s", exc)
        
    return default_opener

async def generate_rephrased_question(question: str, settings: Any) -> str:
    """Generate a simpler, rephrased version of the question for candidate silence."""
    provider = resolve_provider_config(settings)
    if not provider:
        return "Let me ask this a different way: " + question

    system_prompt = (
        "You are an AI interviewer. The candidate has been silent for 15 seconds. "
        "Rephrase the following question to be simpler, or approach it from a different angle "
        "without changing the core topic. Start your response with 'Let me put it another way: ' "
        "or 'Let's try this: '. Maximum 2 sentences. No lists."
    )
    try:
        gen_model = getattr(settings, "interviewer_generator_model", "")
        gen_cfg = _override_model(provider, gen_model)
        
        call_res = await _collect_stream(
            transcript=question,
            system_prompt=system_prompt,
            provider_config=gen_cfg,
            temperature=0.6,
            max_tokens=60,
        )
        if call_res.text:
            return call_res.text
    except Exception as exc:
        logger.warning("Failed to generate rephrased question: %s", exc)
        
    return "Let me ask this a different way: " + question
