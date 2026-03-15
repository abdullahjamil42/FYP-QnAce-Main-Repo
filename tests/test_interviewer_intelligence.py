from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from server.app.intelligence import interviewer
from server.app.intelligence.llm import LLMProviderConfig


def make_settings(**overrides):
    defaults = {
        "normalized_llm_provider": "groq",
        "groq_api_key": "x",
        "groq_model": "llama-3.3-70b-versatile",
        "airforce_api_key": "",
        "airforce_model": "gpt-4o-mini",
        "llm_model": "",
        "llm_max_tokens": 120,
        "interviewer_classifier_model": "llama-3.1-8b-instant",
        "interviewer_generator_model": "llama-3.3-70b-versatile",
        "interviewer_classifier_temperature": 0.0,
        "interviewer_classifier_max_tokens": 220,
        "interviewer_history_window": 3,
        "interviewer_summary_max_chars": 1200,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_parse_classifier_output_valid_json():
    raw = json.dumps(
        {
            "mode": "PROBE_DEPTH",
            "evidence": "Candidate used correct terms but stayed high-level.",
            "follow_up_anchor": "cache invalidation strategy",
            "active_flags": ["bluff", "hint-seeking", "bad-flag"],
        }
    )
    parsed = interviewer._parse_classifier_output(raw)
    assert parsed is not None
    assert parsed["mode"] == "PROBE_DEPTH"
    assert parsed["follow_up_anchor"] == "cache invalidation strategy"
    assert "bluff" in parsed["active_flags"]
    assert "hint-seeking" in parsed["active_flags"]
    assert "bad-flag" not in parsed["active_flags"]


def test_parse_classifier_output_invalid_json_returns_none():
    parsed = interviewer._parse_classifier_output("not-json")
    assert parsed is None


@pytest.mark.asyncio
async def test_classifier_uses_last_3_turns_and_generator_gets_summary(monkeypatch):
    settings = make_settings()
    call_count = {"n": 0}
    captured = {"classifier_payload": None, "generator_payload": None}

    async def fake_stream_llm(transcript, system_prompt, provider_config, temperature=0.7, max_tokens=120):
        call_count["n"] += 1
        payload = json.loads(transcript)

        if call_count["n"] == 1:
            captured["classifier_payload"] = payload
            await asyncio.sleep(0.02)
            yield json.dumps(
                {
                    "mode": "PROBE_DEPTH",
                    "evidence": "Surface-level answer.",
                    "follow_up_anchor": "redis cache",
                    "active_flags": ["bluff"],
                }
            )
            return

        captured["generator_payload"] = payload
        await asyncio.sleep(0.03)
        yield "Right, you mentioned redis cache. "
        yield "What exact eviction policy did you choose and why under real load?"

    monkeypatch.setattr(interviewer, "resolve_provider_config", lambda _s: LLMProviderConfig("groq", "k", "m"))
    monkeypatch.setattr(interviewer, "stream_llm", fake_stream_llm)

    history = [
        {"question": "legacy q0", "answer": "legacy a0", "mode": "PROBE_GAP", "flags": []},
        {"question": "legacy q1", "answer": "legacy a1", "mode": "PROBE_GAP", "flags": []},
        {"question": "legacy q2", "answer": "legacy a2", "mode": "PROBE_GAP", "flags": []},
        {"question": "legacy q3", "answer": "legacy a3", "mode": "PROBE_GAP", "flags": []},
        {"question": "legacy q4", "answer": "legacy a4", "mode": "PROBE_GAP", "flags": []},
    ]

    out = await interviewer.generate_interviewer_turn(
        transcript="We used redis cache and improved p95 by 30 percent.",
        current_question="How did you handle caching?",
        ideal_answer_rubric="Cover trade-offs and measurable impact.",
        rag_passages=["Rubric passage A", "Rubric passage B"],
        rag_distances=[0.6, 0.9],
        vocal_confidence=0.86,
        text_quality_score=62.0,
        text_quality_label="average",
        conversation_history=history,
        previous_mode="PROBE_GAP",
        session_state=None,
        monologue_flag=False,
        next_question="What would you do differently now?",
        settings=settings,
    )

    recent_turns = captured["classifier_payload"]["recent_turns"]
    assert len(recent_turns) == 3
    assert recent_turns[0]["question"] == "legacy q2"
    assert recent_turns[1]["question"] == "legacy q3"
    assert recent_turns[2]["question"] == "legacy q4"

    gen_payload = captured["generator_payload"]
    assert "session_summary" in gen_payload
    assert gen_payload["session_summary"] != ""
    assert out["mode"] == "PROBE_DEPTH"
    assert out["classifier_ms"] > 0.0
    assert out["generator_ms"] > 0.0
    assert out["classifier_ttft_ms"] > 0.0
    assert out["llm_ttft_ms"] > 0.0

    print(
        "interviewer-latency-ms "
        f"classifier_ttft={out['classifier_ttft_ms']} "
        f"classifier_total={out['classifier_ms']} "
        f"generator_ttft={out['llm_ttft_ms']} "
        f"generator_total={out['generator_ms']}"
    )


@pytest.mark.asyncio
async def test_redirect_escalates_on_second_off_topic_turn(monkeypatch):
    settings = make_settings(normalized_llm_provider="none", groq_api_key="")
    monkeypatch.setattr(interviewer, "resolve_provider_config", lambda _s: None)

    state = None
    q = "Explain API idempotency in payment retries."
    off_topic = "I mainly enjoy frontend animations and design systems."

    first = await interviewer.generate_interviewer_turn(
        transcript=off_topic,
        current_question=q,
        ideal_answer_rubric="Discuss idempotency keys and duplicate prevention.",
        rag_passages=[],
        rag_distances=[10.0],
        vocal_confidence=0.4,
        text_quality_score=40.0,
        text_quality_label="poor",
        conversation_history=[],
        previous_mode="",
        session_state=state,
        monologue_flag=False,
        next_question=q,
        settings=settings,
    )
    state = first["state"]

    second = await interviewer.generate_interviewer_turn(
        transcript=off_topic,
        current_question=q,
        ideal_answer_rubric="Discuss idempotency keys and duplicate prevention.",
        rag_passages=[],
        rag_distances=[10.0],
        vocal_confidence=0.4,
        text_quality_score=40.0,
        text_quality_label="poor",
        conversation_history=first["history"],
        previous_mode=first["mode"],
        session_state=state,
        monologue_flag=False,
        next_question=q,
        settings=settings,
    )

    assert first["mode"] == "REDIRECT"
    assert "bring it back" in first["spoken_response"].lower()
    assert second["mode"] == "REDIRECT"
    assert second["spoken_response"] == q


@pytest.mark.asyncio
async def test_monologue_forces_interrupt(monkeypatch):
    settings = make_settings(normalized_llm_provider="none", groq_api_key="")
    monkeypatch.setattr(interviewer, "resolve_provider_config", lambda _s: None)

    out = await interviewer.generate_interviewer_turn(
        transcript="word " * 300,
        current_question="Describe your debugging process.",
        ideal_answer_rubric="Show structured isolation and validation.",
        rag_passages=[],
        rag_distances=[0.5],
        vocal_confidence=0.7,
        text_quality_score=55.0,
        text_quality_label="average",
        conversation_history=[],
        previous_mode="",
        session_state=None,
        monologue_flag=True,
        next_question="What metric did you validate first?",
        settings=settings,
    )

    assert out["mode"] == "INTERRUPT"


@pytest.mark.asyncio
async def test_generator_streams_sentence_chunks_via_callback(monkeypatch):
    settings = make_settings()
    call_count = {"n": 0}
    streamed_chunks: list[str] = []

    async def fake_stream_llm(transcript, system_prompt, provider_config, temperature=0.7, max_tokens=120):
        call_count["n"] += 1
        if call_count["n"] == 1:
            yield json.dumps(
                {
                    "mode": "PROBE_GAP",
                    "evidence": "Partially correct answer.",
                    "follow_up_anchor": "retry logic",
                    "active_flags": [],
                }
            )
            return

        # Generator stream emits two sentence chunks over time.
        yield "Right, you covered retry logic. "
        yield "What backoff strategy did you choose in production? "
        yield "How did it affect timeout rates?"

    async def on_chunk(sentence: str):
        streamed_chunks.append(sentence)

    monkeypatch.setattr(interviewer, "resolve_provider_config", lambda _s: LLMProviderConfig("groq", "k", "m"))
    monkeypatch.setattr(interviewer, "stream_llm", fake_stream_llm)

    out = await interviewer.generate_interviewer_turn(
        transcript="We added retry logic and improved reliability.",
        current_question="How did you improve resilience?",
        ideal_answer_rubric="Cover retries, backoff, and measurable reliability gains.",
        rag_passages=["Use concrete production details."],
        rag_distances=[0.7],
        vocal_confidence=0.8,
        text_quality_score=58.0,
        text_quality_label="average",
        conversation_history=[],
        previous_mode="",
        session_state=None,
        monologue_flag=False,
        next_question="What would you refine next?",
        settings=settings,
        on_generator_sentence_chunk=on_chunk,
    )

    assert out["streamed_chunk_count"] >= 2
    assert len(streamed_chunks) >= 2
    assert streamed_chunks[0].endswith(".") or streamed_chunks[0].endswith("?")
