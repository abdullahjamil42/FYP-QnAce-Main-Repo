"""Q&Ace interviewer intelligence: two-stage classify-then-generate flow."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from .llm import LOCAL_PROVIDER, LLMProviderConfig, resolve_provider_config, stream_llm

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
    re.compile(r"\bwhat\s+kind\s+of\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+type\s+of\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+sort\s+of\b", re.IGNORECASE),
    re.compile(r"\bwhich\s+one\b", re.IGNORECASE),
    re.compile(r"\bcould\s+you\s+repeat\b", re.IGNORECASE),
    re.compile(r"\bcan\s+you\s+repeat\b", re.IGNORECASE),
    re.compile(r"\bsay\s+that\s+again\b", re.IGNORECASE),
    re.compile(r"\bcould\s+you\s+rephrase\b", re.IGNORECASE),
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


CANDIDATE_VOICE_OPENINGS = (
    "i have answered",
    "i already answered",
    "i already said",
    "i just said",
    "as i said",
    "as i mentioned",
    "as i already",
    "why are you asking",
    "you already asked",
    "you just asked",
    "i don't understand why",
    "i do not understand why",
)


def _is_candidate_voice_opening(text: str) -> bool:
    head = (text or "").strip().lower().lstrip("\"'.,!? ")
    # Strip a short acknowledgement prefix if present (mm-hm, okay, right, got it)
    for ack in ("mm-hm", "mmhm", "mm hm", "okay", "ok", "right", "got it", "i see", "interesting"):
        if head.startswith(ack):
            head = head[len(ack):].lstrip(" ,.—-")
            break
    return any(head.startswith(p) for p in CANDIDATE_VOICE_OPENINGS)


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
    return LLMProviderConfig(provider=provider.provider, api_key=provider.api_key, model=model, options=dict(provider.options))


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


def _classifier_system_prompt() -> str:
    return (
        "You are an interview mode classifier. Return JSON only with no prose. "
        "Allowed modes: ADVANCE, PROBE_DEPTH, PROBE_GAP, REDIRECT, CHALLENGE, RESCUE, "
        "INTERRUPT, CONFRONT, ACKNOWLEDGE_IDK, REFRAME. "
        "Output schema: {\"mode\": string, \"evidence\": string, \"follow_up_anchor\": string, "
        "\"active_flags\": [string]}. "
        "Use only active_flags from: contradiction, overclaim, bluff, hint-seeking, hostile. "
        "Evidence must be one sentence. Follow_up_anchor must be a concrete phrase from candidate text. "
        "Never output markdown. Never output anything other than a single valid JSON object."
    )


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


def _build_mode_prompt(mode: str, redirect_count: int, active_flags: list[str], cv_summary: str = "") -> str:
    base = (
        "ROLE LOCK: You are the INTERVIEWER. You are NOT the candidate. "
        "Never speak in the candidate's first-person voice. "
        "Never begin a response with phrases like 'I have answered', 'I already said', 'as I mentioned', 'why are you asking'. "
        "Never echo the candidate's own question back to them as if you were asking it. "
        "You are a senior interviewer at a competitive software company. "
        "You are conducting a live interview and must respond naturally as a real person would. "
        "Tone is warm but direct, like a curious and experienced colleague. "
        "Begin with a brief, varied natural acknowledgement (for example: mm-hm, got it, okay, right, interesting) — keep it under four words and do not reuse the same one repeatedly. "
        "Do not use bullet points, headers, lists, or markdown formatting. "
        "Do not say great answer, absolutely, or give reflexive praise. "
        "Do not reveal the rubric or the ideal answer. "
        "Do NOT restate or repeat the original question back to the candidate — they have already heard it. "
        "Your response MUST reference the candidate's actual answer — quote or paraphrase what they said. "
        "Keep your response to 2 spoken sentences maximum, optimized for text-to-speech. "
        "The payload contains candidate_transcript (the answer you are responding to RIGHT NOW) and recent_turns (earlier Q/A pairs, for continuity only). "
        "You MUST only quote, paraphrase, or reference candidate_transcript. "
        "NEVER quote, paraphrase, or attribute content from recent_turns to the candidate as if they just said it — those are prior turns, already addressed. "
        "If candidate_transcript is empty, one word, or clearly does not address current_question, acknowledge that and restate the question — do not invent content the candidate did not say."
    )
    if cv_summary:
        base += (
            " You have the candidate's CV summary below — when it is relevant, "
            "ground your probe in specific projects, skills, or experience they listed. "
            "Do not invent details that are not in the CV.\n"
            "CV SUMMARY:\n" + cv_summary[:1200]
        )

    mode_directives = {
        "ADVANCE": (
            "Briefly acknowledge one specific thing the candidate said well. "
            "Do NOT say or repeat the next question — it will be asked separately after you finish. "
            "Keep to 1–2 short sentences only. Do not over-praise."
        ),
        "PROBE_DEPTH": (
            "The candidate's answer is surface-level but on the right track. "
            "Pick a specific claim or phrase from their answer and ask them to go deeper. "
            "For example, if they said they 'used caching', ask what caching strategy, what eviction policy, "
            "and what the cache hit rate was. Be specific to THEIR answer, not generic. "
            "IMPORTANT: You are continuing the same question — do NOT introduce a new topic. "
            "Reference something the candidate just said. Keep it to 1–2 sentences. "
            "Do NOT start with 'Can you tell me about' or 'What is your experience with' — those are new-question openers."
        ),
        "PROBE_GAP": (
            "The candidate missed an important dimension of the question. "
            "Acknowledge what they covered, then ask about the specific missing part. "
            "Your follow-up should sound like a natural clarifying question from an experienced interviewer, "
            "not a teacher correcting a student. "
            "IMPORTANT: You are continuing the same question — do NOT introduce a new topic. "
            "Reference something the candidate just said. Keep it to 1–2 sentences. "
            "Do NOT start with 'Can you tell me about' or 'What is your experience with' — those are new-question openers."
        ),
        "REDIRECT": (
            "The candidate's answer is off-topic or not addressing the question. "
            "If this is the first redirect, gently steer back: 'I appreciate that context, but let me bring us back to...'. "
            "If second redirect, restate the question directly."
        ),
        "CHALLENGE": (
            "The candidate made bold claims without specifics. "
            "Ask for one concrete example: a specific decision THEY made, a real number, or a measurable result. "
            "Sound curious, not accusatory — like you genuinely want to understand their contribution. "
            "IMPORTANT: You are continuing the same question — do NOT introduce a new topic. "
            "Keep it to 1–2 sentences max."
        ),
        "RESCUE": (
            "The candidate is clearly stuck or struggling. Be supportive without giving away the answer. "
            "Simplify the question or offer a starting angle: 'Let me put it this way...' or "
            "'What if we narrow this down to just...'. Help them find solid ground. "
            "IMPORTANT: You are continuing the same question — do NOT introduce a new topic. "
            "Keep it to 1–2 sentences."
        ),
        "INTERRUPT": (
            "The candidate has been talking too long. Politely interject: "
            "'Let me pause you there.' Then pick the most interesting thing from the second half "
            "of their answer and ask a focused question about just that."
        ),
        "CONFRONT": (
            "The candidate contradicted something they said earlier. "
            "Bring it up non-accusatorily: 'Earlier you mentioned X, but just now you said Y. "
            "Can you help me understand which is accurate?'"
        ),
        "ACKNOWLEDGE_IDK": (
            "The candidate admitted they do not know. Respond supportively: "
            "'That is okay, not everyone has experience with that.' "
            "Then move to the next question naturally."
        ),
        "REFRAME": (
            "The candidate asked for clarification. Answer their question briefly and specifically, "
            "then redirect them to answer. Do not repeat the entire question. "
            "IMPORTANT: You are continuing the same question — do NOT introduce a new topic. "
            "Keep your clarification to 1–2 sentences."
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
            "mode": "INTERRUPT",
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
    elif len(answer.split()) <= 6 and _jaccard(answer, current_question) < 0.25:
        mode = "REDIRECT"
    elif "bluff" in active_flags:
        mode = "CHALLENGE"
    elif text_quality_score >= 78.0 and rag_relevance >= 0.45:
        mode = "ADVANCE"
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
        return "Okay, good. Let us move forward."
    if mode == "PROBE_DEPTH":
        return f"You mentioned {anchor}. Can you walk me through the specific steps you took and what the outcome was?"
    if mode == "PROBE_GAP":
        return f"That is a good start. I noticed you did not touch on {anchor} though. How would you approach that part specifically?"
    if mode == "REDIRECT":
        if redirect_count <= 1:
            return "I appreciate the context. Let us bring it back to the original question though."
        return "Let us refocus on the original question."
    if mode == "CHALLENGE":
        if "overclaim" in active_flags:
            return "I would like to understand your personal contribution. What specific decision did you make, and what measurable result did it produce?"
        return "Can you give me a concrete example from your own experience? I am looking for a specific situation, what you did, and the result."
    if mode == "RESCUE":
        return "No worries. Let us simplify this. What is the first thing that comes to mind when you think about this problem? Start there."
    if mode == "INTERRUPT":
        return f"Let me pause you there. You mentioned {anchor}. Can you summarize your main point in one sentence?"
    if mode == "CONFRONT":
        return f"Before we move on, I want to clarify something. {contradiction_evidence} Which one is accurate?"
    if mode == "ACKNOWLEDGE_IDK":
        return "That is completely fine. Let us move on."
    if mode == "REFRAME":
        return "Let me rephrase that. Think about a specific situation you have been in. What decisions did you make and what trade-offs were involved?"
    return "Let us continue."


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
    cv_summary: str = "",
    on_generator_sentence_chunk: Optional[Callable[[str], Awaitable[None]]] = None,
) -> dict[str, Any]:
    """Run classifier call then generator call and update persistent interviewer state."""
    state = _ensure_state(session_state)

    history = list(conversation_history or state.get("turn_history", []))
    history_window = max(1, int(getattr(settings, "interviewer_history_window", 3)))
    summary_max_chars = max(300, int(getattr(settings, "interviewer_summary_max_chars", 1200)))

    q_stats = _question_stats(state, current_question)
    rag_relevance = _estimate_rag_relevance(rag_distances)

    turn_index = len(history) + 1
    new_claims = _extract_claims(transcript, current_question, turn_index)
    contradiction_evidence = _find_contradiction(new_claims, state.get("key_claims", []))

    active_flags: list[str] = []
    if contradiction_evidence:
        active_flags.append("contradiction")
    if _detect_overclaim(transcript):
        active_flags.append("overclaim")
    if _detect_bluff(transcript, vocal_confidence, text_quality_score, rag_relevance):
        active_flags.append("bluff")
    if _detect_hint_seeking(transcript):
        active_flags.append("hint-seeking")
    if _detect_hostile(transcript):
        active_flags.append("hostile")

    provider = resolve_provider_config(settings)
    classifier_result: Optional[dict[str, Any]] = None
    classifier_ms = 0.0
    classifier_ttft_ms = 0.0

    answer_norm = _normalize_text(transcript)
    answer_words = len(answer_norm.split())
    if answer_words <= 6 and _jaccard(answer_norm, current_question) < 0.25:
        # Short + low overlap with current question. Run the deterministic
        # classifier — it already routes to REFRAME / ACKNOWLEDGE_IDK / RESCUE /
        # REDIRECT as appropriate. Skipping the cloud classifier prevents it
        # from hallucinating an anchor from recent_turns.
        classifier_result = _fallback_classification(
            transcript=transcript,
            current_question=current_question,
            rag_relevance=0.0,
            vocal_confidence=vocal_confidence,
            text_quality_score=text_quality_score,
            active_flags=active_flags,
            monologue_flag=False,
        )
        classifier_result["follow_up_anchor"] = ""

    recent_turns = _last_n_turns(history, history_window)
    # Drop meta / frustration turns so the generator LLM does not echo them
    # back as if the candidate just said them.
    META_ANSWER_PATTERNS = (
        "why are you asking",
        "i have answered",
        "i already answered",
        "you already asked",
        "you just asked",
        "asked me this",
    )
    recent_turns = [
        t for t in recent_turns
        if not any(
            p in (_normalize_text(str(t.get("answer", "")))).lower()
            for p in META_ANSWER_PATTERNS
        )
    ]
    previous_mode_norm = (previous_mode or "").strip().upper()
    if previous_mode_norm not in MODES and state.get("last_modes"):
        previous_mode_norm = str(state["last_modes"][-1]).upper()

    classifier_payload = {
        "candidate_transcript": _normalize_text(transcript),
        "current_question": _normalize_text(current_question),
        "ideal_answer_rubric": _normalize_text(ideal_answer_rubric)[:1200],
        "rag_relevance": round(rag_relevance, 3),
        "vocal_confidence": round(_clamp(vocal_confidence, 0.0, 1.0), 3),
        "text_quality_score": round(_clamp(text_quality_score, 0.0, 100.0), 1),
        "text_quality_label": _normalize_text(text_quality_label),
        "recent_turns": recent_turns,
        "previous_mode": previous_mode_norm,
        "seed_flags": active_flags,
    }

    # Local provider: skip LLM classifier — evaluator adapter is fine-tuned for
    # coaching feedback text, not structured JSON output, so the classifier call
    # always fails to parse and wastes 2-4s. Use deterministic fallback directly.
    if provider is not None and provider.provider != LOCAL_PROVIDER:
        try:
            cls_model = getattr(settings, "interviewer_classifier_model", "")
            cls_cfg = _override_model(provider, cls_model)
            cls_temp = _safe_float(getattr(settings, "interviewer_classifier_temperature", 0.0), 0.0)
            cls_tokens = int(getattr(settings, "interviewer_classifier_max_tokens", 220))
            cls_call = await _collect_stream(
                json.dumps(classifier_payload, ensure_ascii=True),
                _classifier_system_prompt(),
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
        classifier_result = _fallback_classification(
            transcript=transcript,
            current_question=current_question,
            rag_relevance=rag_relevance,
            vocal_confidence=vocal_confidence,
            text_quality_score=text_quality_score,
            active_flags=active_flags,
            monologue_flag=monologue_flag,
        )

    mode = str(classifier_result.get("mode", "PROBE_GAP")).upper()
    evidence = _normalize_text(str(classifier_result.get("evidence", ""))) or "Mode selected by policy."
    follow_up_anchor = _normalize_text(str(classifier_result.get("follow_up_anchor", "")))
    if follow_up_anchor:
        anchor_norm = follow_up_anchor.lower().strip()
        transcript_norm = _normalize_text(transcript).lower()
        if anchor_norm not in transcript_norm:
            words = anchor_norm.split()
            ok = False
            for i in range(len(words) - 3):
                if " ".join(words[i:i + 4]) in transcript_norm:
                    ok = True
                    break
            if not ok:
                logger.info("Rejecting classifier anchor (not in current answer): %r", follow_up_anchor)
                follow_up_anchor = ""
    cls_flags = [f for f in classifier_result.get("active_flags", []) if f in ALLOWED_FLAGS]
    for f in active_flags:
        if f not in cls_flags:
            cls_flags.append(f)

    # Hard safety overrides.
    if monologue_flag:
        mode = "INTERRUPT"
    if "contradiction" in cls_flags:
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

    # Generator sees compressed session arc summary.
    session_summary = state.get("session_summary", "")
    if not session_summary:
        session_summary = _compress_session_summary(history, summary_max_chars)

    generator_prompt = _build_mode_prompt(mode, redirect_count, cls_flags, cv_summary=cv_summary)
    logger.info(
        "Interviewer turn: mode=%s q=%r transcript=%r anchor=%r",
        mode,
        _normalize_text(current_question)[:60],
        _normalize_text(transcript)[:60],
        follow_up_anchor[:60],
    )
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

    spoken_response = ""
    generator_ttft_ms = 0.0
    generator_ms = 0.0
    streamed_chunk_count = 0

    # Local models are small and hallucinate badly on template-friendly modes
    # (they tend to echo the candidate's voice or repeat the question). Skip
    # the generator and use the deterministic _fallback_spoken template for
    # those modes instead.
    TEMPLATE_MODES = {"REDIRECT", "REFRAME", "ACKNOWLEDGE_IDK", "RESCUE", "ADVANCE"}
    is_local_provider = provider is not None and provider.provider == LOCAL_PROVIDER
    skip_generator = is_local_provider and mode in TEMPLATE_MODES
    if skip_generator:
        logger.info("Skipping generator LLM for local provider + mode=%s", mode)

    if provider is not None and not skip_generator:
        try:
            gen_model = getattr(settings, "interviewer_generator_model", "")
            gen_cfg = _override_model(provider, gen_model)
            t_gen_start = time.perf_counter()
            tokens: list[str] = []
            pending = ""
            emitted_sentences: list[str] = []
            sentence_limit = 3
            rejected_candidate_voice = False
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
                    if not emitted_sentences and _is_candidate_voice_opening(sentence):
                        logger.warning(
                            "Rejecting candidate-voice generator opening: %r",
                            sentence[:120],
                        )
                        rejected_candidate_voice = True
                        break
                    emitted_sentences.append(sentence)
                    if on_generator_sentence_chunk is not None:
                        try:
                            await on_generator_sentence_chunk(sentence)
                            streamed_chunk_count += 1
                        except Exception as exc:
                            logger.warning("Generator chunk callback failed (%s)", exc)
                    if len(emitted_sentences) >= sentence_limit:
                        break
                if rejected_candidate_voice or len(emitted_sentences) >= sentence_limit:
                    break

            if (
                not rejected_candidate_voice
                and pending.strip()
                and len(emitted_sentences) < sentence_limit
            ):
                tail = _normalize_text(pending)
                if tail and not (not emitted_sentences and _is_candidate_voice_opening(tail)):
                    emitted_sentences.append(tail)
                    if on_generator_sentence_chunk is not None:
                        try:
                            await on_generator_sentence_chunk(tail)
                            streamed_chunk_count += 1
                        except Exception as exc:
                            logger.warning("Generator tail callback failed (%s)", exc)

            if rejected_candidate_voice:
                spoken_response = ""
            else:
                spoken_response = _normalize_text(" ".join(emitted_sentences))
                if not spoken_response:
                    spoken_response = _normalize_text("".join(tokens))
                    if _is_candidate_voice_opening(spoken_response):
                        logger.warning(
                            "Rejecting candidate-voice generator output (unsegmented): %r",
                            spoken_response[:120],
                        )
                        spoken_response = ""

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

    # Keep TTS-friendly output constraints.
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
        "classifier_ms": round(classifier_ms, 1),
        "classifier_ttft_ms": round(classifier_ttft_ms, 1),
        "generator_ms": round(generator_ms, 1),
        "llm_ttft_ms": round(generator_ttft_ms, 1),
        "streamed_chunk_count": streamed_chunk_count,
        "rag_relevance": round(rag_relevance, 3),
    }
