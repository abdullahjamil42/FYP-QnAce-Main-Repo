"""
Q&Ace — WebRTC Signaling (POST /offer → SDP answer).

- Receives browser SDP offer.
- Creates aiortc RTCPeerConnection.
- Sets up audio track consumption → VAD → STT pipeline.
- Returns SDP answer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import random
import uuid
from typing import Any, Callable

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("qace.signaling")
router = APIRouter()

# ── In-memory session store ──
_sessions: dict[str, dict[str, Any]] = {}
_semantic_detector: Any = None

INTRO_QUESTION = (
    "Welcome to your interview. Please start with a short introduction: "
    "your background, your current role, and one project you are proud of."
)

SKIP_PHRASES = [
    "Alright, let's move on to the next question.",
    "No worries, let's continue with the next one.",
    "Okay, moving forward to the next question.",
    "Let's keep the momentum going. Next question.",
    "That's fine, let's proceed to the next topic.",
]

SILENCE_TIMEOUT_SECONDS = 10

# ── Acknowledgment phrase pools (Feature 3) ──────────────────────────────
ACKNOWLEDGMENT_PHRASES = {
    "high": ["Great, thank you.", "Got it, appreciate that.",
             "That's helpful context.", "Good, makes sense.",
             "Okay, noted.", "Right, thank you."],
    "medium": ["Okay, thank you.", "Alright.", "Sure, okay.",
               "Got it.", "Mm, okay.", "Right."],
    "low": ["Okay.", "Alright, moving on.", "Sure."],
}

# ── Mode-aware acknowledgment phrases (Gap 2) ────────────────────────────
# Empty list = no acknowledgment spoken before this mode's follow-up.
MODE_ACKNOWLEDGMENTS: dict[str, list] = {
    "PROBE_DEPTH": [
        "Interesting — let me push on that a bit.",
        "Okay, I want to dig into that further.",
        "That's a useful framing. Let me ask you something more specific.",
    ],
    "PROBE_GAP": [
        "I see.",
        "Got it.",
        "Okay — I want to make sure I understand.",
    ],
    "CHALLENGE": [
        "Hmm. I want to push back on something you said.",
        "Let me pause you there for a second.",
    ],
    "REDIRECT": [],   # No ack — should feel abrupt
    "RESCUE": [],     # No ack — jump straight in
    "INTERRUPT": [],  # No ack — polite interjection is already in the probe text
    "CONFRONT": [],   # No ack — confrontation should not be softened
    "ADVANCE_HIGH": ["Great, thank you.", "That's clear, thank you."],
    "ADVANCE_MED":  ["Okay, got it.", "Understood."],
    "ADVANCE_LOW":  ["Alright.", "Okay, let's move on."],
}

# ── Fallback encouragement phrases ───────────────────────────────────────
_ENCOURAGEMENT_PHRASES = [
    "Take your time, I'm listening.",
    "No rush, whenever you're ready.",
]


def _compute_blinks_per_min(blink_history: list) -> float:
    """Compute blinks per minute from AU45 history using peak detection."""
    if len(blink_history) < 10:
        return 17.5  # not enough data yet
    values = [v for _, v in blink_history[-300:]]  # last 30s @ 10Hz
    threshold = 0.4
    in_blink = False
    blink_count = 0
    for v in values:
        if v > threshold and not in_blink:
            blink_count += 1
            in_blink = True
        elif v < threshold * 0.5:
            in_blink = False
    duration_min = len(values) / 10.0 / 60.0
    if duration_min < 0.05:
        return 17.5
    return round(blink_count / duration_min, 2)


def _build_question_prompt(session: dict[str, Any], q_index: int) -> str:
    """Build the spoken prompt for a given question index."""
    questions = session.get("question_bank", [])
    if q_index < 0 or q_index >= len(questions):
        return ""
    q = questions[q_index]
    if q_index == 0:
        return f"Great introduction. First question: {q.get('text', '')}"
    return f"Next question: {q.get('text', '')}"


def _voice_for_question_type(question_type: str) -> str:
    """Female for HR/closing questions, male for technical ones."""
    return "female" if question_type in ("behavioral", "closing", "intro") else "male"


def _get_current_voice(session: dict[str, Any]) -> str:
    """Return the voice assigned to the current question (set at question start)."""
    return session.get("current_voice", "male")


def _get_voice_name(session: dict[str, Any], settings: Any) -> str:
    """Return the TTS voice name for the current turn."""
    voice = _get_current_voice(session)
    if voice == "female":
        return getattr(settings, "tts_voice_female", "en-US-JennyNeural")
    return getattr(settings, "tts_voice", "en-US-GuyNeural")


def _get_semantic_detector(settings: Any) -> Any:
    """Lazy singleton semantic detector shared across sessions."""
    global _semantic_detector
    if not getattr(settings, "semantic_vad_enabled", True):
        return None
    if _semantic_detector is not None:
        return _semantic_detector
    try:
        from ..vad.semantic_turn_detector import SemanticTurnDetector

        _semantic_detector = SemanticTurnDetector(
            min_silence_ms=settings.semantic_min_silence_ms,
            max_silence_ms=settings.semantic_max_silence_ms,
            semantic_threshold=settings.semantic_threshold,
            model_name=settings.semantic_model,
        )
        logger.info(
            "Semantic VAD enabled ✓ (min=%dms max=%dms threshold=%.2f)",
            settings.semantic_min_silence_ms,
            settings.semantic_max_silence_ms,
            settings.semantic_threshold,
        )
    except Exception as exc:
        logger.warning("Semantic VAD init failed (%s) — using silence-only VAD", exc)
        _semantic_detector = None
    return _semantic_detector


async def _speak_session_text(
    session: dict[str, Any],
    dc: Any,
    text: str,
    send_status_fn: Callable[[Any, str], None],
    started_at: float | None = None,
    voice: str | None = None,
) -> float:
    """Speak text over the TTS track and return first-audio latency in ms."""
    tts_eng = session.get("tts_engine")
    tts_track = session.get("tts_track")
    if tts_eng is None or tts_track is None or not text.strip():
        return 0.0

    from ..config import get_settings
    from ..synthesis.tts import split_text_for_tts_streaming

    settings = get_settings()
    max_chars = max(60, int(getattr(settings, "tts_chunk_max_chars", 150)))
    use_sentence_streaming = bool(getattr(settings, "tts_sentence_streaming", True))

    if use_sentence_streaming:
        chunks = split_text_for_tts_streaming(text, max_chars=max_chars)
    else:
        chunks = [text[:max_chars]] if len(text) > max_chars else [text]

    if not chunks:
        return 0.0

    first_audio_ms = 0.0
    total_duration_s = 0.0
    session["speaking"] = True
    send_status_fn(dc, f"tts-stream: chunks={len(chunks)} max_chars={max_chars}")

    for idx, chunk in enumerate(chunks):
        synth_t0 = time.perf_counter()
        tts_result = await tts_eng.synthesize(chunk, voice=voice)
        if tts_result.audio_pcm is None or len(tts_result.audio_pcm) == 0:
            continue

        tts_track.enqueue_audio(tts_result.audio_pcm, tts_result.sample_rate)
        total_duration_s += float(tts_result.duration_s)

        if idx == 0:
            first_audio_ms = (time.perf_counter() - (started_at if started_at is not None else synth_t0)) * 1000.0

        rms = float(np.sqrt(np.mean(tts_result.audio_pcm.astype(np.float32) ** 2))) / 32768.0
        session["audio_energy"] = rms

    if total_duration_s > 0.0:
        send_status_fn(dc, f"tts: {total_duration_s:.1f}s via {getattr(tts_eng, 'engine_name', 'tts')}")
        await asyncio.sleep(total_duration_s)

    session["speaking"] = False
    session["audio_energy"] = 0.0
    return first_audio_ms


async def _coding_debrief_flow(
    session: dict[str, Any],
    dc: Any,
    scoring: dict[str, Any],
) -> None:
    """Avatar speaks coding feedback + LLM follow-up, then returns to answering phase."""
    from ..config import get_settings
    from ..intelligence.llm import call_llm, resolve_provider_config
    from ..webrtc.data_channel import send_phase, send_question, send_status

    settings = get_settings()
    send_status(dc, "coding-debrief: start")

    correctness = scoring.get("correctness") or {}
    passed = int(correctness.get("passed", 0))
    total = int(correctness.get("total", 0))
    complexity = scoring.get("complexity") or {}
    time_c = complexity.get("time", "unknown")
    failed = correctness.get("failed_cases") or []
    is_optimal = bool(complexity.get("is_optimal", True))

    if passed < total:
        pattern = "some edge cases"
        if failed and isinstance(failed, list) and failed and isinstance(failed[0], dict):
            pattern = str(failed[0].get("error") or failed[0].get("actual") or "edge cases")[:120]
        script = (
            f"Your solution passes {passed} out of {total} cases. "
            f"It looks like it struggles with {pattern}. Walk me through your approach."
        )
    else:
        if is_optimal:
            script = (
                f"Your solution passes all {total} test cases. "
                f"Great work — it runs in {time_c}. Walk me through your approach."
            )
        else:
            script = (
                f"Your solution passes all {total} cases in {time_c}. "
                "Walk me through your approach and how you might improve it further."
            )

    voice_name = _get_voice_name(session, settings)
    session["current_phase"] = "speaking"
    send_phase(dc, "speaking", 0)
    await _speak_session_text(session, dc, script, send_status, voice=voice_name)

    follow_up = "What trade-offs did you consider when you chose this approach?"
    provider = resolve_provider_config(settings)
    if provider:
        try:
            raw = await call_llm(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are an interviewer. Ask ONE short follow-up question about the candidate's "
                            "code or algorithm. Plain text only, one or two sentences max."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Scoring JSON:\n{json.dumps(scoring)[:6000]}",
                    },
                ],
                provider,
                temperature=0.45,
                max_tokens=160,
                timeout_s=20.0,
            )
            if raw and not _is_unusable_llm_feedback(raw):
                follow_up = raw.strip()
        except Exception as exc:
            logger.warning("coding follow-up LLM failed: %s", exc)

    session["current_phase"] = "answering"
    send_phase(dc, "answering", 0)
    send_question(
        dc,
        follow_up,
        -2,
        1,
        "coding_followup",
        _get_current_voice(session),
    )
    await _speak_session_text(session, dc, follow_up, send_status, voice=voice_name)
    send_status(dc, "coding-debrief: complete")


def _build_fallback_feedback(
    transcript: str,
    text_quality_label: str,
    filler_count: int,
    wpm: float,
) -> str:
    """Generate a short local fallback response when no hosted LLM is configured."""
    pace_hint = "slow down slightly" if wpm > 175 else "add a little more detail" if wpm < 110 else "keep that pace"
    filler_hint = "Reduce filler words on the next answer." if filler_count > 0 else "Keep the answer crisp and specific."
    structure_hint = (
        "Use Situation, Task, Action, and Result to make the example concrete."
        if text_quality_label in {"poor", "average"}
        else "Good structure. Add one measurable outcome to make it stronger."
    )
    preview = transcript.strip()
    if len(preview) > 48:
        preview = preview[:48].rstrip() + "..."
    return (
        f"I heard: {preview}. {structure_hint} {filler_hint} For your next response, {pace_hint}."
    )


def _is_unusable_llm_feedback(text: str) -> bool:
    """Return True for provider errors or placeholder text that should not be spoken."""
    normalized = text.strip().lower()
    if not normalized:
        return True
    patterns = (
        "[airforce error",
        "[groq error",
        "[llm ",
        "[httpx ",
        "model does not exist",
        "rate limit exceeded",
        "too many requests",
        "response malformed",
        "llm unavailable",
    )
    return any(pattern in normalized for pattern in patterns)

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription
    from aiortc.contrib.media import MediaRelay

    _AIORTC_AVAILABLE = True
    _relay = MediaRelay()
except ImportError:
    _AIORTC_AVAILABLE = False
    _relay = None
    logger.warning("aiortc not installed — WebRTC endpoints will return 503")


class OfferRequest(BaseModel):
    sdp: str
    type: str = "offer"
    job_role: str = "software_engineer"
    interview_type: str = "quick"


class AnswerResponse(BaseModel):
    sdp: str
    type: str = "answer"
    session_id: str


from fastapi import Depends as _Depends
from ..auth import require_user as _require_user


@router.post("/offer", response_model=AnswerResponse)
async def handle_offer(req: OfferRequest, user_id: str | None = _Depends(_require_user)):
    """SDP offer → answer exchange. Sets up the full audio pipeline."""
    if not _AIORTC_AVAILABLE:
        raise HTTPException(503, "WebRTC runtime (aiortc) not available")

    from ..config import get_settings
    from ..models import registry
    from ..intelligence.rag import retrieve as rag_retrieve
    from ..intelligence.scoring import InterviewScoringEngine, RunningScorer, UtteranceScores
    from ..perception.stt import transcribe
    from ..perception.text_quality import classify_quality, classify_quality_llm
    from ..perception.vocal import analyze as vocal_analyze
    from ..vad.ring_buffer import RingBuffer
    from ..vad.silero import EndOfSpeechDetector
    from ..webrtc.data_channel import (
        send_status, send_transcript, send_scores, send_perception,
        send_phase, send_question, send_interview_end,
        parse_au_telemetry,
    )
    from ..webrtc.tracks import consume_audio_track
    from ..webrtc.tracks import TTSAudioStreamTrack, AvatarVideoStreamTrack

    settings = get_settings()
    session_id = str(uuid.uuid4())
    pc = RTCPeerConnection()
    ring = RingBuffer(max_seconds=30.0, sample_rate=16_000)

    from ..intelligence.question_bank import generate_question_set
    from ..intelligence.cv import fetch_and_parse_cv, generate_cv_questions

    # Fetch + parse CV (cached per hash). Non-fatal on failure.
    cv_profile = await fetch_and_parse_cv(user_id, settings)
    cv_qs: list[str] = []
    if not cv_profile.is_empty():
        target_cv_qs = 3 if req.interview_type == "quick" else 4
        try:
            cv_qs = await generate_cv_questions(
                cv_profile, req.job_role, target_cv_qs, settings,
            )
        except Exception as exc:
            logger.warning("CV question generation failed: %s", exc)
            cv_qs = []

    question_bank = generate_question_set(
        job_role=req.job_role,
        interview_type=req.interview_type,
        cv=cv_profile if not cv_profile.is_empty() else None,
        cv_questions=cv_qs or None,
    )
    logger.info(
        "Session %s: %s interview for %s, %d questions (cv=%s, cv_qs=%d)",
        session_id[:8], req.interview_type, req.job_role, len(question_bank),
        "yes" if not cv_profile.is_empty() else "no", len(cv_qs),
    )

    session: dict[str, Any] = {
        "id": session_id,
        "pc": pc,
        "ring": ring,
        "data_channel": None,
        "au_channel": None,
        "latest_au": None,
        "blink_history": [],
        "latest_face_emotion": "neutral",
        "audio_task": None,
        "transcribe_tasks": set(),
        "transcribe_lock": asyncio.Lock(),
        "analysis_lock": asyncio.Lock(),
        "transcribe_running": False,
        "pending_audio": None,
        "stt_model": registry.whisper_model,
        "stt_device": getattr(registry, "whisper_model_device", None),
        "scorer": RunningScorer(),
        "interview_scorer": InterviewScoringEngine(),
        # Phase 4 synthesis state
        "tts_engine": getattr(registry, "tts_engine", None),
        "avatar_engine": getattr(registry, "avatar_engine", None),
        "speaking": False,
        "audio_energy": 0.0,
        "interview_stage": "intro",
        "interview_question_idx": 0,
        "interview_started": False,
        "latest_partial_transcript": "",
        "latest_transcript_text": "",
        # Interview config
        "job_role": req.job_role,
        "interview_type": req.interview_type,
        "question_bank": question_bank,
        "cv_profile": cv_profile,
        "cv_summary": cv_profile.to_prompt_summary() if not cv_profile.is_empty() else "",
        "answered_count": 0,
        "skipped_count": 0,
        "per_question_scores": [],
        "current_phase": "idle",
        "phase_timer_task": None,
        "silence_timer_task": None,
        "last_speech_time": None,
        "interview_complete": False,
        # Feature 1: Completion detection state
        "current_answer_transcript": "",
        "silence_since_last_speech": None,
        "last_completeness_score": 0.0,
        "last_completeness_signals": {},
        "answer_prompted_at": None,
        "answer_prompted_spoken": False,
        "current_question_subtype": "unknown",
        "answer_fallback_task": None,
        "vad_speaking": False,
        "last_backchannel_time": 0.0,
        "current_q_probe_count": 0,
        "post_transcript_in_flight": False,
        # Feature 4: Backchannel state
        "last_backchannel_time": None,
        "backchannel_active": False,
        "backchannel_track": None,
        "backchannel_log": [],
        # Bug fixes + realism gaps
        "transition_lock": asyncio.Lock(),          # Bug 4: atomic transition guard
        "is_probe_cycle": False,                    # Bug 2: stricter silence after probes
        "_pending_inflight_result": None,           # Bug 3: re-trigger after in-flight
        "_pending_inflight_audio": None,            # Bug 3
        "interviewer_voice": random.choice(["male", "female"]),  # Gap 3: locked per session
        "last_interviewer_mode": "",               # Gap 2: mode-aware ack
        "soft_prompt_sent": False,                 # Gap 5: mid-silence nonverbal at 5s
    }
    _sessions[session_id] = session

    # ── Outbound media tracks (server → client) ──
    tts_track = TTSAudioStreamTrack(output_rate=48_000)
    avatar_track = AvatarVideoStreamTrack(
        avatar_engine=session.get("avatar_engine"),
        session=session,
        fps=settings.avatar_fps,
    )

    # Feature 4: Backchannel audio track
    from ..synthesis.backchannel import BackchannelTrack, BackchannelManager
    backchannel_track = BackchannelTrack()
    session["backchannel_track"] = backchannel_track
    backchannel_mgr = BackchannelManager(
        session=session,
        tts_engine=session.get("tts_engine"),
        backchannel_track=backchannel_track,
    )
    session["tts_track"] = tts_track
    session["avatar_track"] = avatar_track
    pc.addTrack(tts_track)
    pc.addTrack(avatar_track)
    pc.addTrack(backchannel_track)  # Feature 4: backchannel audio

    # ── Interview flow management ──

    async def _start_question_flow(q_index: int) -> None:
        """Start the speak → answer flow for a question.

        This is the single source of truth for question progression.
        The flow is strictly sequential and fully awaited:
          1. Classify question subtype (behavioral/technical/situational)
          2. Send question text to client (appears on screen)
          3. Speak the question via TTS (await full playback)
          4. Answer phase — completeness-based detection via _post_transcript

        _post_transcript triggers completeness evaluation and _check_advance.
        """
        dc = session.get("data_channel")

        # Fix 4: _start_question_flow must never be entered while the intro is
        # still in progress — the intro is handled by _begin_interview and
        # _answer_fallback_timer(-1).  If this fires during intro it means a
        # regression introduced a second delivery path for question_bank[0].
        if session.get("interview_stage") == "intro":
            logger.error(
                "_start_question_flow(%d) called while interview_stage='intro' — "
                "aborting to prevent duplicate question delivery",
                q_index,
            )
            return

        # Ensure local LLM is in neutral 'none' mode (clear evaluator bias)
        # Only do this at the very beginning of the interview
        if q_index == 0:
            from ..intelligence.llm import resolve_provider_config, swap_adapter
            provider = resolve_provider_config(settings)
            if provider and provider.provider == "local":
                send_status(dc, "initializing neutral interviewer mode...")
                await swap_adapter("none")
        questions = session.get("question_bank", [])
        if q_index >= len(questions) or session.get("interview_complete"):
            await _end_interview()
            return

        # Idempotency guard: if we already started this exact question and it's
        # still in speaking/answering, do not re-enter (prevents duplicate TTS
        # of the same question when a stray VAD/transition triggers re-entry).
        started_idx = session.get("question_started_idx")
        current_phase = session.get("current_phase", "")
        if (
            started_idx == q_index
            and current_phase in ("speaking", "answering")
            and not session.get("interview_complete")
        ):
            logger.info("Skipping duplicate _start_question_flow(%d), phase=%s", q_index, current_phase)
            return
        session["question_started_idx"] = q_index

        _cancel_all_timers()

        session["interview_question_idx"] = q_index + 1
        session["interview_stage"] = "questions"
        session["current_q_transcripts"] = 0

        # Reset per-question completeness state
        session["current_answer_transcript"] = ""
        session["silence_since_last_speech"] = None
        session["last_completeness_score"] = 0.0
        session["last_completeness_signals"] = {}
        session["answer_prompted_spoken"] = False
        session["current_q_probe_count"] = 0
        session["fallback_timer_epoch"] = session.get("fallback_timer_epoch", 0) + 1
        session["is_probe_cycle"] = False       # Bug 2: bank question resets probe flag
        session["soft_prompt_sent"] = False     # Gap 5: reset per question
        if session.get("backchannel_active"):
            session["backchannel_active"] = False

        q = questions[q_index]
        # Gap 3: voice locked per session at bootstrap, not per question type
        session["current_voice"] = session.get("interviewer_voice", "male")
        voice_label = _get_current_voice(session)
        voice_name = _get_voice_name(session, settings)

        # 1. Classify question subtype
        try:
            from ..intelligence.coverage import classify_question_subtype
            from ..intelligence.llm import resolve_provider_config
            provider_cfg = resolve_provider_config(settings)
            subtype = await classify_question_subtype(
                q.get("text", ""), q.get("type", "role_specific"), provider_cfg,
            )
        except Exception:
            subtype = "behavioral"
        session["current_question_subtype"] = subtype

        # Set phase=speaking BEFORE any await so the VAD callback can't fire
        # on_speech_start/end during this window with phase=="answering".
        session["current_phase"] = "speaking"
        session["speaking"] = True
        session["current_question"] = q.get("text", "")

        # 2. Send question text to client so it appears on screen
        send_question(dc, q.get("text", ""), q_index, len(questions), q.get("type", ""), voice_label)
        send_phase(dc, "speaking", 0)

        # 3. Speak the question via TTS — await FULL playback
        spoken = _build_question_prompt(session, q_index)
        if spoken:
            await _speak_session_text(session, dc, spoken, send_status, voice=voice_name)

        # 4. Enter ANSWER phase — completeness-based detection
        # Bug 1: drain VAD hardware buffer tail before re-enabling speech detection
        session["speaking"] = False
        await asyncio.sleep(0.30)
        session["current_phase"] = "answering"
        session["last_speech_time"] = time.perf_counter()
        session["answer_prompted_at"] = time.perf_counter()
        send_phase(dc, "answering", 0)
        send_status(dc, "phase: answering")

        # Start fallback timer (encouragement at 12s, auto-skip at 20s)
        session["answer_fallback_task"] = asyncio.create_task(
            _answer_fallback_timer(q_index, session["fallback_timer_epoch"])
        )

    async def _check_advance(q_index: int) -> None:
        """Check if the answer is complete enough to advance.

        Called reactively after each completeness evaluation.
        Conditions:
          - High Score (>= 0.70): Advance after 1.5s silence.
          - Low Score (< 0.70): Advance after 6.0s silence (auto-finish).
          - Intro (-1): Advance if score >= 0.40 and 2.5s silence.
        """
        if session.get("current_phase") != "answering":
            return
        if session.get("interview_complete"):
            return

        silence_since = session.get("silence_since_last_speech")
        if silence_since is None:
            return
        silence_dur = time.perf_counter() - silence_since

        score = session.get("last_completeness_score", 0.0)
        
        # Determine threshold based on phase
        is_intro = (q_index == -1)
        target_score = 0.40 if is_intro else 0.70
        high_score_silence = 2.5 if is_intro else 1.5
        # Bug 2: probe answers are naturally short/focused — score faster but
        # candidate may still be mid-thought. Give extra breathing room.
        if session.get("is_probe_cycle") and not is_intro:
            high_score_silence = 3.0
        low_score_silence = 6.0
        
        should_force = False
        if score >= target_score:
            if silence_dur < high_score_silence:
                return
        else:
            # Low score — only advance if silent for a long time
            if silence_dur < low_score_silence:
                return
            should_force = True

        dc = session.get("data_channel")
        signals = session.get("last_completeness_signals", {})
        
        # Send answer_complete event
        from .data_channel import send_answer_complete
        send_answer_complete(dc, score, signals)

        reason = "forced (silence)" if should_force else "complete"
        send_status(dc, f"answer-advance ({reason}): score={score:.2f}")
        session["answered_count"] = session.get("answered_count", 0) + 1

        # Cancel fallback timer and bump epoch so stale timers self-exit
        ft = session.get("answer_fallback_task")
        if ft and not ft.done():
            ft.cancel()
        session["fallback_timer_epoch"] = session.get("fallback_timer_epoch", 0) + 1

        await _transition_to_next(q_index)

    async def _answer_fallback_timer(q_index: int, my_epoch: int = 0) -> None:
        """Persistent monitor for the answer phase.
        
        Controls:
        - 12s total silence (no speech ever) -> encouragement
        - 20s total silence (no speech ever) -> skip
        - 6s silence after speech (regardless of score) -> advance
        - Prevents interruptions if vad_speaking is True
        """
        phase_start = time.perf_counter()
        encouraged = False
        
        while session.get("current_phase") == "answering":
            await asyncio.sleep(0.5)

            # Epoch guard: if a newer timer has been created (e.g. after a
            # follow-up reset), this stale instance must exit immediately.
            if session.get("fallback_timer_epoch", 0) != my_epoch:
                logger.debug("Fallback timer epoch %d stale (current %d), exiting",
                             my_epoch, session.get("fallback_timer_epoch", 0))
                return

            if session.get("interview_complete"):
                return

            # If _post_transcript is in-flight, do NOT advance.
            # The pipeline may take 10-20s and will handle advancement itself.
            if session.get("post_transcript_in_flight"):
                continue

            # If STT transcription is still running, the user DID speak — don't
            # treat the processing gap as silence and fire encouragement/skip.
            if session.get("transcribe_running"):
                continue

            # If VAD is currently detecting speech, skip checks.
            # Safety: if EOS detector says no speech but vad_speaking is stuck,
            # reset it (happens with short noise bursts from TTS echo).
            if session.get("vad_speaking"):
                eos = session.get("eos_detector")
                if eos and not eos.is_speaking:
                    session["vad_speaking"] = False
                else:
                    continue

            last_speech = session.get("last_speech_time")
            has_spoken = int(session.get("current_q_transcripts", 0)) > 0
            
            now = time.perf_counter()
            total_silence = now - phase_start
            post_speech_silence = (now - last_speech) if last_speech else total_silence

            # 1. User spoke but then went silent for 6s → force advance
            #    NOTE: We cannot call _check_advance here because it cancels
            #    the fallback task (us!), which raises CancelledError and kills
            #    the transition. Instead, transition directly.
            if has_spoken and post_speech_silence >= 6.0:
                dc = session.get("data_channel")
                score = session.get("last_completeness_score", 0.0)
                signals = session.get("last_completeness_signals", {})
                from .data_channel import send_answer_complete
                send_answer_complete(dc, score, signals)
                send_status(dc, f"answer-advance (forced-silence-6s): score={score:.2f}")
                session["answered_count"] = session.get("answered_count", 0) + 1
                await _transition_to_next(q_index)
                return

            # Gap 5: Nonverbal soft prompt at ~5s (before encouragement at 12s)
            if not has_spoken and total_silence >= 5.0 and not session.get("soft_prompt_sent"):
                session["soft_prompt_sent"] = True
                from .data_channel import send_event
                send_event(dc, "interviewer_prompt", {"type": "nonverbal"})
                send_status(dc, "soft-prompt: nonverbal at 5s")

            # 2. Never spoke at all for 12s -> Encourage
            if not has_spoken and total_silence >= 12.0 and not encouraged:
                encouraged = True
                session["answer_prompted_spoken"] = True
                dc = session.get("data_channel")
                phrase = random.choice(_ENCOURAGEMENT_PHRASES)
                voice_name = _get_voice_name(session, settings)
                send_status(dc, f"encouragement: {phrase}")
                await _speak_session_text(session, dc, phrase, send_status, voice=voice_name)

            # 3. Never spoke at all for 20s -> Skip
            if not has_spoken and total_silence >= 20.0:
                dc = session.get("data_channel")
                send_status(dc, "silence-timeout: 20s, skipping question")
                if q_index >= 0:
                    session["skipped_count"] = session.get("skipped_count", 0) + 1
                await _transition_to_next(q_index)
                return

    async def _transition_to_next(current_q_index: int) -> None:
        """Speak acknowledgment, then advance to the next question."""
        # Bug 4: Use a per-session lock so that concurrent callers
        # (_check_advance + _answer_fallback_timer) cannot both enter the
        # transition body.  The phase check inside the lock is still needed
        # because the lock is reentrant across non-overlapping calls.
        async with session["transition_lock"]:
            # Guard: re-check phase inside the lock (TOCTOU safety)
            if session.get("current_phase") not in ("answering", "transition"):
                return
            if session.get("current_phase") == "transition":
                return  # Another transition already started
            dc = session.get("data_channel")
            session["current_phase"] = "transition"
            send_phase(dc, "transition", 0)

            # Cancel fallback timer if still running (but not if WE are the fallback timer)
            current = asyncio.current_task()
            ft = session.get("answer_fallback_task")
            if ft and not ft.done() and ft is not current:
                ft.cancel()

            # Wait for in-flight post_transcript to finish before transitioning.
            # Skip if pt_task IS the current task (called from within _post_transcript_inner)
            # to avoid a self-deadlock where the task waits for itself.
            pt_task = session.get("post_transcript_task")
            if pt_task and not pt_task.done() and pt_task is not current:
                try:
                    await asyncio.wait_for(asyncio.shield(pt_task), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("post_transcript timed out during transition, proceeding")
                except Exception:
                    pass

            # Reset probe count for the next question
            session["current_q_probe_count"] = 0

            # Feature 3 / Gap 2: Mode-aware acknowledgment phrase (skip on intro)
            q_idx = int(session.get("interview_question_idx", 0))
            if q_idx >= 1:  # Don't ack the intro (idx 0)
                last_mode = session.get("last_interviewer_mode", "")
                # Use mode-specific pool if present and non-empty
                mode_pool = MODE_ACKNOWLEDGMENTS.get(last_mode, None)
                if mode_pool:
                    ack_phrase = random.choice(mode_pool)
                elif mode_pool is None:
                    # Unknown mode — fall back to score-based bands
                    score = session.get("last_completeness_score", 0.0)
                    if score >= 0.75:
                        ack_key = "ADVANCE_HIGH"
                    elif score >= 0.45:
                        ack_key = "ADVANCE_MED"
                    else:
                        ack_key = "ADVANCE_LOW"
                    ack_phrase = random.choice(MODE_ACKNOWLEDGMENTS.get(ack_key, ACKNOWLEDGMENT_PHRASES["medium"]))
                else:
                    # mode_pool is empty list — skip acknowledgment (e.g. REDIRECT, RESCUE)
                    ack_phrase = ""
                if ack_phrase:
                    voice_name = _get_voice_name(session, settings)
                    send_status(dc, f"ack ({last_mode or 'score'}): {ack_phrase}")
                    await _speak_session_text(session, dc, ack_phrase, send_status, voice=voice_name)
                    await asyncio.sleep(0.4)  # 400ms pause after ack

            next_idx = int(session.get("interview_question_idx", 0))
            questions = session.get("question_bank", [])
            if next_idx < len(questions):
                await _start_question_flow(next_idx)
            else:
                await _end_interview()

    def _cancel_all_timers() -> None:
        """Cancel all running timer/monitor tasks (except the caller)."""
        current = asyncio.current_task()
        for key in ("phase_timer_task", "silence_timer_task", "answer_monitor_task", "answer_fallback_task"):
            old = session.get(key)
            if old and not old.done() and old is not current:
                old.cancel()

    async def _end_interview() -> None:
        """Finalize the interview and notify the client."""
        if session.get("interview_complete"):
            return
        session["interview_complete"] = True
        session["current_phase"] = "complete"
        _cancel_all_timers()
        dc = session.get("data_channel")

        questions = session.get("question_bank", [])
        answered = session.get("answered_count", 0)
        skipped = session.get("skipped_count", 0)

        # Aggregate raw per-utterance records into one score per question index.
        raw_per_q: list[dict] = session.get("per_question_scores", [])
        buckets: dict[int, list[dict]] = {}
        for rec in raw_per_q:
            idx = rec["index"]
            buckets.setdefault(idx, []).append(rec)
        per_q_summary = []
        for idx in sorted(buckets):
            recs = buckets[idx]
            n = len(recs)
            per_q_summary.append({
                "index": idx,
                "question": recs[0]["question"],
                "score": round(sum(r["score"] for r in recs) / n, 1),
                "content": round(sum(r["content"] for r in recs) / n, 1),
                "delivery": round(sum(r["delivery"] for r in recs) / n, 1),
                "composure": round(sum(r["composure"] for r in recs) / n, 1),
                "skipped": recs[0].get("skipped", False),
            })
        avg_total = (
            round(sum(q["score"] for q in per_q_summary) / len(per_q_summary), 1)
            if per_q_summary else 0.0
        )
        send_interview_end(dc, len(questions), answered, skipped, per_q_summary, avg_total)
        send_phase(dc, "complete", 0)

        closing = (
            "That concludes your interview. Great job staying focused. "
            "Your scores and detailed feedback will be available on the summary page."
        )
        voice_name = _get_voice_name(session, settings)
        await _speak_session_text(session, dc, closing, send_status, voice=voice_name)
        send_status(dc, f"interview-complete: {answered} answered, {skipped} skipped out of {len(questions)}")

    async def _post_transcript(result, audio_chunk):
        """Run scoring, perception, and completeness evaluation for a transcript.

        Triggers _check_advance() after completeness evaluation.
        """
        # Phase guard: only process transcripts during answering phase
        current_phase = session.get("current_phase", "")
        if current_phase not in ("answering", "intro"):
            logger.debug("Ignoring transcript in phase %s", current_phase)
            return

        # NEW: Noise filter. Ignore very short transcripts (TTS echo, noise bursts)
        # to stop ghost VAD triggers and unnecessary LLM latency.
        transcript_text = (result.text or "").strip()
        word_count = len(transcript_text.split())
        if word_count < 4 and current_phase != "intro":
            logger.info("Ignoring noisy transcript (%d words): '%s'", word_count, transcript_text)
            return

        # Guard: if another pipeline is already in-flight, accumulate the
        # transcript text AND stash the full result for a follow-up run after
        # the current pipeline finishes (Bug 3: prevents dead-ends when a new
        # speech segment arrives during scoring).
        if session.get("post_transcript_in_flight"):
            session["current_answer_transcript"] = (
                session.get("current_answer_transcript", "") + " " + transcript_text
            ).strip()
            session["current_q_transcripts"] = int(session.get("current_q_transcripts", 0)) + 1
            session["last_speech_time"] = time.perf_counter()
            session["silence_since_last_speech"] = time.perf_counter()
            # Stash latest pending — overwrite any prior stash so we always
            # re-process the most-recent segment after the current run ends.
            session["_pending_inflight_result"] = result
            session["_pending_inflight_audio"] = audio_chunk
            logger.info(
                "Pipeline in-flight, stashed pending transcript (%d segments): '%s'",
                session.get("current_q_transcripts", 0),
                transcript_text[:60],
            )
            return

        # Guard: prevent fallback timer from advancing while this pipeline runs
        session["post_transcript_in_flight"] = True
        try:
            await _post_transcript_inner(result, audio_chunk)
        finally:
            session["post_transcript_in_flight"] = False
            # Bug 3: if a new segment arrived while we were running, process it now
            pending_result = session.pop("_pending_inflight_result", None)
            pending_audio = session.pop("_pending_inflight_audio", None)
            if pending_result is not None and session.get("current_phase") == "answering":
                logger.info("Re-triggering pipeline for pending transcript segment")
                asyncio.ensure_future(_post_transcript(pending_result, pending_audio))

    async def _post_transcript_inner(result, audio_chunk):
        """Inner implementation of post_transcript (wrapped by in-flight guard)."""
        session["current_q_transcripts"] = int(session.get("current_q_transcripts", 0)) + 1

        # Accumulate transcript for completeness analysis
        session["current_answer_transcript"] = (
            session.get("current_answer_transcript", "") + " " + result.text
        ).strip()

        # Restart fallback timer loop (if not already running)
        # However, _answer_fallback_timer is now a persistent while loop started in _start_question_flow.
        # So we don't need to restart it here.
        # But we DO need to ensure it wasn't cancelled.
        ft = session.get("answer_fallback_task")
        if ft is None or ft.done():
            q_idx = max(-1, int(session.get("interview_question_idx", 1)) - 1)
            session["answer_fallback_task"] = asyncio.create_task(
                _answer_fallback_timer(q_idx)
            )

        dc = session.get("data_channel")
        loop = asyncio.get_running_loop()
        dur_s = len(audio_chunk) / 16_000
        t_pipeline_start = time.perf_counter()

        try:
            # 1-2-6. Run TQ + Vocal + RAG in parallel
            t_percept = time.perf_counter()
            tq_backend = getattr(settings, "text_quality_backend", "llm").strip().lower()
            if tq_backend == "llm":
                tq_fut = classify_quality_llm(result.text, settings)
            elif tq_backend == "heuristic":
                from ..perception.text_quality import _heuristic_quality
                tq_fut = loop.run_in_executor(None, _heuristic_quality, result.text)
            else:
                tq_fut = loop.run_in_executor(
                    None,
                    classify_quality,
                    result.text,
                    getattr(registry, "bert_model", None),
                    getattr(registry, "bert_tokenizer", None),
                )
            vocal_fut = loop.run_in_executor(
                None,
                vocal_analyze,
                audio_chunk,
                getattr(registry, "vocal_model", None),
            )
            rag_fut = loop.run_in_executor(None, rag_retrieve, result.text)

            tq_result, vocal_result, rag_result = await asyncio.gather(
                tq_fut, vocal_fut, rag_fut,
            )
            percept_ms = (time.perf_counter() - t_percept) * 1000.0
            tq_ms = tq_result.inference_ms
            vocal_ms = vocal_result.inference_ms
            rag_ms = rag_result.retrieval_ms

            # 3. AU telemetry snapshot
            au = session.get("latest_au")
            eye_contact = au.eye_contact if au else 0.5
            blinks_per_min = _compute_blinks_per_min(session.get("blink_history", []))
            # Map vocal + face emotion to positivity (50/50 blend)
            positive_emotions = {"confident", "composed", "engaged", "happy", "positive"}
            vocal_positive = vocal_result.dominant_emotion in positive_emotions
            face_emotion = session.get("latest_face_emotion", "neutral")
            face_positive = face_emotion in positive_emotions
            emotion_positivity = ((0.7 if vocal_positive else 0.3) + (0.7 if face_positive else 0.3)) / 2.0

            # 4. Compute scores (master interview scoring engine)
            interview_scorer: InterviewScoringEngine = session.get("interview_scorer")
            telemetry = {
                "bert_classification": tq_result.label,
                "bert_base_score": tq_result.base_score,
                "llm_star_evaluation": tq_result.base_score,
                "whisper_wpm": result.wpm,
                "whisper_filler_count": result.filler_count,
                "whisper_word_count": len(result.text.split()) if result.text else 0,
                "whisper_duration_s": dur_s,
                "wav2vec2_confidence": vocal_result.acoustic_confidence,
                "mediapipe_eye_contact": eye_contact,
                "mediapipe_bpm": blinks_per_min,
                "action_units": [],
                "emotion_timeline": [],
                "question_subtype": session.get("current_question_subtype", "unknown"),
            }
            interview_scores = interview_scorer.evaluate_session(telemetry)

            latest_scores = UtteranceScores(
                content=float(interview_scores["Sub_Scores"]["Content"]),
                delivery=float(interview_scores["Sub_Scores"]["Delivery"]),
                composure=float(interview_scores["Sub_Scores"]["Composure"]),
                final=float(interview_scores["Final_Score"]),
                fluency=float(interview_scores["Details"].get("fluency", 0.0)),
                vocal_confidence=round(float(vocal_result.acoustic_confidence), 3),
                eye_contact=round(float(eye_contact), 3),
                blink_deviation=round(abs(float(blinks_per_min) - 17.5) / 17.5, 3),
                emotion_positivity=round(float(emotion_positivity), 3),
                text_quality_score=round(float(tq_result.base_score), 1),
            )

            session["scorer"].add(latest_scores)
            scores_payload = session["scorer"].to_dict()
            scores_payload["deduction_flags"] = interview_scores.get("Deduction_Flags", [])
            scores_payload["details"] = interview_scores.get("Details", {})
            send_scores(dc, scores_payload)
            send_status(dc, f"scores: {latest_scores.final:.1f}/100")
            if interview_scores.get("Deduction_Flags"):
                send_status(dc, f"score-flags: {', '.join(interview_scores['Deduction_Flags'])}")

            # 5. Send perception
            send_perception(dc, {
                "vocal_emotion": vocal_result.dominant_emotion,
                "face_emotion": session.get("latest_face_emotion", "neutral"),
                "text_quality_label": tq_result.label,
                "text_quality_score": tq_result.base_score,
                "acoustic_confidence": vocal_result.acoustic_confidence,
                "parallel_wall_ms": round(percept_ms, 1),
                "total_wall_ms": round(percept_ms, 1),
            })
            send_status(dc, f"perception: vocal={vocal_result.dominant_emotion} quality={tq_result.label}")

            # 6. RAG context
            rubric_context = "\n---\n".join(rag_result.passages) if rag_result.passages else ""
            if rubric_context:
                send_status(dc, f"rag: {len(rag_result.passages)} passages in {rag_ms:.0f}ms")

            # 7. Record per-question score
            q_idx = max(0, int(session.get("interview_question_idx", 1)) - 1)
            questions = session.get("question_bank", [])
            q_record = {
                "index": q_idx,
                "question": session.get("current_question", ""),
                "score": latest_scores.final,
                "content": latest_scores.content,
                "delivery": latest_scores.delivery,
                "composure": latest_scores.composure,
                "skipped": False,
            }
            per_q = session.get("per_question_scores", [])
            per_q.append(q_record)
            session["per_question_scores"] = per_q

            session["last_speech_time"] = time.perf_counter()

            # 8. Optional LLM feedback (Groq or Airforce)
            llm_ttft_ms = 0.0
            classifier_ms = 0.0
            generator_ms = 0.0
            word_count = len(result.text.split())
            send_status(dc, f"interview: answer received ({word_count} words)")

            from ..intelligence import interviewer as interviewer_intel

            current_question = str(session.get("current_question") or INTRO_QUESTION)
            interviewer_state = session.get("interviewer_state")
            conversation_history = session.get("interviewer_history") or []
            previous_modes = (interviewer_state or {}).get("last_modes", [])
            previous_mode = previous_modes[-1] if previous_modes else ""
            monologue_flag = bool(
                word_count >= max(10, int(getattr(settings, "interview_interrupt_word_limit", 250)))
            )
            next_q_idx = int(session.get("interview_question_idx", 0))
            # Fix 1: during intro the first bank question must not be leaked to
            # the LLM or fallback — _start_question_flow is the sole delivery
            # point for that question.
            if session.get("interview_stage") == "intro":
                next_prompt_text = None
            else:
                next_prompt_text = ""
                if next_q_idx < len(questions):
                    next_prompt_text = questions[next_q_idx].get("text", "")

            # Pass the full accumulated answer so the LLM sees everything the
            # user has said for this question, not just the latest segment.
            full_answer_so_far = session.get("current_answer_transcript") or result.text
            turn_result = await interviewer_intel.generate_interviewer_turn(
                transcript=full_answer_so_far,
                current_question=current_question,
                ideal_answer_rubric=rubric_context,
                rag_passages=list(rag_result.passages or []),
                rag_distances=list(rag_result.distances or []),
                vocal_confidence=float(vocal_result.acoustic_confidence),
                text_quality_score=float(tq_result.base_score),
                text_quality_label=str(tq_result.label),
                conversation_history=conversation_history,
                previous_mode=previous_mode,
                session_state=interviewer_state,
                monologue_flag=monologue_flag,
                next_question=next_prompt_text if next_prompt_text is not None else "Thank you for your introduction.",
                settings=settings,
                cv_summary=session.get("cv_summary", ""),
            )

            session["interviewer_state"] = turn_result.get("state")
            session["interviewer_history"] = turn_result.get("history", conversation_history)
            llm_ttft_ms = float(turn_result.get("llm_ttft_ms", 0.0))
            classifier_ms = float(turn_result.get("classifier_ms", 0.0))
            generator_ms = float(turn_result.get("generator_ms", 0.0))

            mode = str(turn_result.get("mode") or "PROBE_GAP")
            spoken = str(turn_result.get("spoken_response") or "")

            # Gap 2: Record the current mode for use in _transition_to_next ack
            session["last_interviewer_mode"] = mode

            # Track probes per question — cap at 2, then force ADVANCE
            probe_count = session.get("current_q_probe_count", 0)
            PROBE_MODES = {"PROBE_DEPTH", "PROBE_GAP", "CHALLENGE", "REDIRECT", "RESCUE", "CONFRONT", "REFRAME"}
            if mode in PROBE_MODES:
                probe_count += 1
                session["current_q_probe_count"] = probe_count
                if probe_count > 2:
                    mode = "ADVANCE"
                    spoken = ""  # Let the normal transition handle speech
                    logger.info("Probe cap reached (%d), forcing ADVANCE", probe_count)

            if spoken and not _is_unusable_llm_feedback(spoken):
                from ..webrtc.data_channel import send_event
                send_event(dc, "interviewer_feedback", {"text": spoken, "mode": mode})

                # ── Phase 2: Speak the follow-up via TTS ──
                if mode != "ADVANCE":
                    # Set phase to "speaking" so new transcripts are rejected
                    # by the phase guard in _post_transcript while follow-up plays.
                    session["current_phase"] = "speaking"
                    send_phase(dc, "speaking", 0)
                    voice_name = _get_voice_name(session, settings)
                    send_status(dc, f"speaking follow-up ({mode})")
                    # Gap 1: Human-like thinking pause before probe TTS (0.6–1.2s)
                    await asyncio.sleep(random.uniform(0.6, 1.2))
                    await _speak_session_text(session, dc, spoken, send_status, voice=voice_name)
                    # Update current_question to the probe text so the next answer
                    # is evaluated in the context of this follow-up, not the original Q.
                    session["current_question"] = spoken

            send_status(dc, f"interview-mode: {mode}")
            send_status(
                dc,
                (
                    "interviewer-latency: "
                    f"classifier={classifier_ms:.0f}ms "
                    f"generator={generator_ms:.0f}ms "
                    f"ttft={llm_ttft_ms:.0f}ms"
                ),
            )

            # 9. Latency summary (advancement is handled by completeness evaluation)
            total_ms = (time.perf_counter() - t_pipeline_start) * 1000.0
            latency_report = (
                f"latency: percept={percept_ms:.0f}ms(tq={tq_ms:.0f}+vocal={vocal_ms:.0f}+rag={rag_ms:.0f}) "
                f"interviewer=cls:{classifier_ms:.0f}ms+gen:{generator_ms:.0f}ms "
                f"llm_ttft={llm_ttft_ms:.0f}ms "
                f"total={total_ms:.0f}ms"
            )
            logger.info("Pipeline %s", latency_report)
            send_status(dc, latency_report)

            # Feature 1: Completeness evaluation + mode-based advancement
            if mode == "ADVANCE":
                # Normal advancement path — completeness check decides when to move on
                try:
                    from ..intelligence.completeness import evaluate_completeness
                    from ..intelligence.llm import resolve_provider_config

                    full_transcript = session.get("current_answer_transcript", "")
                    question_text = session.get("current_question", "")
                    question_subtype = session.get("current_question_subtype", "unknown")
                    audio_tail = session.get("_last_audio_tail", audio_chunk)
                    provider_cfg = resolve_provider_config(settings)

                    completeness = await evaluate_completeness(
                        full_transcript=full_transcript,
                        question_text=question_text,
                        question_subtype=question_subtype,
                        audio_tail=audio_tail,
                        sample_rate=16_000,
                        provider_config=provider_cfg,
                    )

                    session["last_completeness_score"] = completeness.score
                    session["last_completeness_signals"] = {
                        "semantic": completeness.semantic,
                        "prosodic": completeness.prosodic,
                        "coverage": completeness.coverage,
                    }

                    # Check if we should advance
                    q_idx = max(-1, int(session.get("interview_question_idx", 1)) - 1)
                    await _check_advance(q_idx)

                except Exception as comp_exc:
                    logger.warning("Completeness evaluation failed: %s", comp_exc)
            else:
                # Non-ADVANCE mode (follow-up spoken) — reset completeness state
                # so the user can re-answer and the fallback timer doesn't
                # immediately force-advance past the follow-up.

                # STEP 1: Kill the old fallback timer FIRST (before changing phase)
                # to close the race window where the old timer sees phase=answering
                # with a stale phase_start and fires _transition_to_next.
                ft = session.get("answer_fallback_task")
                current = asyncio.current_task()
                if ft and not ft.done() and ft is not current:
                    ft.cancel()

                # STEP 2: Bump the timer epoch so any stale timer iteration that
                # slips past the cancel() harmlessly exits on its next loop check.
                new_epoch = session.get("fallback_timer_epoch", 0) + 1
                session["fallback_timer_epoch"] = new_epoch

                # STEP 3: Now safe to reset answer state and set phase to answering.
                # Bug 1: drain VAD hardware buffer tail before re-enabling speech detection
                session["speaking"] = False
                await asyncio.sleep(0.30)
                session["current_phase"] = "answering"
                send_phase(dc, "answering", 0)
                session["current_q_transcripts"] = 0
                session["current_answer_transcript"] = ""
                session["last_completeness_score"] = 0.0
                session["last_completeness_signals"] = {}
                session["silence_since_last_speech"] = None
                session["last_speech_time"] = time.perf_counter()
                session["post_transcript_in_flight"] = False
                session["is_probe_cycle"] = True     # Bug 2: stricter silence after probes
                session["soft_prompt_sent"] = False  # Gap 5: re-arm for re-answer

                # STEP 4: Start fresh fallback timer with the new epoch.
                q_idx = max(-1, int(session.get("interview_question_idx", 1)) - 1)
                session["answer_fallback_task"] = asyncio.create_task(
                    _answer_fallback_timer(q_idx, new_epoch)
                )
                send_status(dc, f"awaiting re-answer after {mode} follow-up")

        except Exception as exc:
                logger.exception("Post-transcript pipeline failed: %s", exc)
                send_status(dc, f"pipeline-error: {exc}")

    async def transcribe_and_send(audio_chunk):
        """Run final STT off the event loop, then send one stable transcript."""
        try:
            dc = session.get("data_channel")
            dur_s = len(audio_chunk) / 16_000
            send_status(dc, f"transcribing {dur_s:.1f}s audio…")
            loop = asyncio.get_running_loop()
            current_chunk = audio_chunk
            while current_chunk is not None:
                model = session.get("stt_model") or registry.whisper_model
                model_device = session.get("stt_device") or getattr(registry, "whisper_model_device", None)
                timeout_s = max(15.0, dur_s * 4.0)

                try:
                    async with session["transcribe_lock"]:
                        result = await asyncio.wait_for(
                            loop.run_in_executor(
                                None,
                                transcribe,
                                current_chunk,
                                model,
                            ),
                            timeout=timeout_s,
                        )
                except asyncio.TimeoutError:
                    logger.warning(
                        "STT timed out after %.1fs on %s for session %s",
                        timeout_s,
                        model_device,
                        session_id[:8],
                    )
                    send_status(dc, f"stt-timeout after {timeout_s:.0f}s on {model_device or 'unknown'}")

                    cpu_model = registry.load_whisper_cpu(settings.model_dir, settings.whisper_model)
                    if cpu_model is None:
                        send_status(dc, "stt-fallback unavailable")
                        result = None
                    else:
                        # Update both session AND global registry so all
                        # future sessions use CPU directly instead of
                        # re-trying the broken CUDA model.
                        session["stt_model"] = cpu_model
                        session["stt_device"] = "cpu"
                        registry.whisper_model = cpu_model
                        registry.whisper_model_device = "cpu"
                        logger.info("Switched global STT to CPU fallback")
                        send_status(dc, "retrying transcription on cpu…")
                        async with session["transcribe_lock"]:
                            result = await loop.run_in_executor(
                                None,
                                transcribe,
                                current_chunk,
                                cpu_model,
                            )

                if result is None:
                    current_chunk = session.get("pending_audio")
                    session["pending_audio"] = None
                    continue

                dc = session.get("data_channel")
                if result.text:
                    session["latest_transcript_text"] = result.text
                    session["latest_partial_transcript"] = result.text
                    send_transcript(
                        dc,
                        result.text,
                        result.inference_ms,
                        result.wpm,
                        result.filler_count,
                    )
                    send_status(dc, f"transcript: {result.text[:60]}")
                    # Fire scoring + perception + RAG + LLM pipeline
                    pt_task = asyncio.create_task(_post_transcript(result, current_chunk))
                    session["post_transcript_task"] = pt_task
                elif result.inference_ms == 0:
                    logger.warning("Transcription returned empty (model may not be loaded)")
                    send_status(dc, "stt-empty: model may not be loaded")
                else:
                    send_status(dc, f"stt-empty after {result.inference_ms:.0f}ms (silence?)")

                current_chunk = session.get("pending_audio")
                session["pending_audio"] = None
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Async transcription failed: %s", exc)
        finally:
            session["transcribe_running"] = False
            pending = session.get("pending_audio")
            if pending is not None:
                session["pending_audio"] = None
                session["transcribe_running"] = True
                task = asyncio.create_task(transcribe_and_send(pending))
                session["transcribe_tasks"].add(task)
                task.add_done_callback(lambda t: session["transcribe_tasks"].discard(t))

    def on_speech_start():
        # Drop any VAD activation while TTS is playing (speaker bleed-through).
        if session.get("speaking") or session.get("current_phase") == "speaking":
            return
        # Only track during answering phase to avoid TTS echo issues
        if session.get("current_phase") == "answering":
            logger.info("on_speech_start fired")
            session["vad_speaking"] = True

    def on_speech_end(audio_chunk):
        # Don't process audio captured while TTS is playing (echo rejection).
        # The VAD may trigger on speaker bleed-through — discard it.
        if session.get("speaking"):
            logger.debug("Ignoring speech_end during TTS playback (echo)")
            return

        chunk = audio_chunk.copy()
        dur_s = len(chunk) / 16_000
        logger.info("on_speech_end fired: %.2fs audio", dur_s)
        session["vad_speaking"] = False
        session["last_speech_time"] = time.perf_counter()
        session["silence_since_last_speech"] = time.perf_counter()

        # Feature 4: Notify backchannel manager
        backchannel_mgr.on_speech_end()

        # Store audio tail for prosodic analysis
        session["_last_audio_tail"] = chunk

        dc = session.get("data_channel")
        send_status(dc, f"speech-end detected ({dur_s:.1f}s)")
        if session.get("transcribe_running"):
            session["pending_audio"] = chunk
            send_status(dc, "queued (transcriber busy)")
            return

        session["transcribe_running"] = True
        task = asyncio.create_task(transcribe_and_send(chunk))
        session["transcribe_tasks"].add(task)
        task.add_done_callback(lambda t: session["transcribe_tasks"].discard(t))

    eos_detector = EndOfSpeechDetector(
        silence_ms=settings.vad_silence_ms,
        min_speech_s=settings.vad_min_speech_s,
        silero_session=registry.silero_vad,
        on_speech_start=on_speech_start,
        on_speech_end=on_speech_end,
        semantic_turn_detector=_get_semantic_detector(settings),
        partial_transcript_provider=lambda: (
            session.get("latest_partial_transcript")
            or session.get("latest_transcript_text")
            or ""
        ),
    )
    session["eos_detector"] = eos_detector

    async def _consume_video_track(track: Any) -> None:
        """Sample video frames at 2 FPS and run face emotion classification."""
        from ..perception import face as face_module
        last_sample = 0.0
        SAMPLE_INTERVAL = 0.5  # 2 FPS is enough for emotion tracking
        while True:
            try:
                frame = await asyncio.wait_for(track.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break
            now = time.perf_counter()
            if now - last_sample < SAMPLE_INTERVAL:
                continue
            last_sample = now
            face_model = getattr(registry, "face_model", None)
            if face_model is None:
                continue
            try:
                img = frame.to_ndarray(format="rgb24")
                h, w = img.shape[:2]
                size = min(h, w)
                y0, x0 = (h - size) // 2, (w - size) // 2
                crop = img[y0:y0 + size, x0:x0 + size]
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, face_module.classify, crop, face_model
                )
                session["latest_face_emotion"] = result.dominant_emotion
            except Exception as exc:
                logger.debug("Face emotion sampling error: %s", exc)

    @pc.on("track")
    async def on_track(track):
        logger.info("Track received: %s (%s)", track.kind, track.id)
        if track.kind == "audio":
            session["audio_task"] = asyncio.create_task(
                consume_audio_track(
                    track,
                    ring,
                    eos_detector,
                    session,
                )
            )
        elif track.kind == "video":
            session["video_task"] = asyncio.create_task(
                _consume_video_track(track)
            )

    @pc.on("datachannel")
    def on_datachannel(channel):
        logger.info("DataChannel '%s' opened", channel.label)

        if channel.label == "qace-events":
            session["data_channel"] = channel
            send_status(channel, "server-datachannel-ready")
            avatar_eng = session.get("avatar_engine")
            avatar_engine_name = getattr(avatar_eng, "engine_name", "none") if avatar_eng is not None else "none"
            send_status(channel, f"avatar-engine: {avatar_engine_name}")
            send_status(channel, f"avatar-image: {settings.avatar_image}")

            if not session.get("interview_started", False):
                session["interview_started"] = True
                questions = session.get("question_bank", [])
                send_status(channel, f"interview-config: {session.get('job_role')} {session.get('interview_type')} ({len(questions)} questions)")
                session["current_voice"] = "female"  # Intro is an HR/behavioral question
                voice_name = _get_voice_name(session, settings)

                send_question(channel, INTRO_QUESTION, -1, len(questions), "intro", _get_current_voice(session))

                async def _begin_interview():
                    # Speak the intro question — await full playback
                    session["current_phase"] = "speaking"
                    send_phase(channel, "speaking", 0)
                    await _speak_session_text(session, channel, INTRO_QUESTION, send_status, voice=voice_name)

                    # After TTS finishes, start answering for the intro
                    session["interview_stage"] = "intro"
                    session["interview_question_idx"] = 0
                    session["current_question"] = INTRO_QUESTION
                    session["current_q_transcripts"] = 0
                    session["current_phase"] = "answering"
                    session["last_speech_time"] = time.perf_counter()
                    send_phase(channel, "answering", 0)
                    send_status(channel, "phase: answering (unlimited) — introduce yourself")

                    # Monitor handles advancement after answer/silence
                    session["answer_fallback_task"] = asyncio.create_task(
                        _answer_fallback_timer(-1)
                    )

                asyncio.create_task(_begin_interview())

            @channel.on("message")
            def on_message(message):
                if isinstance(message, str):
                    try:
                        import json

                        payload = json.loads(message)
                        if isinstance(payload, dict):
                            msg_type = payload.get("type", "")
                            if msg_type == "partial_transcript":
                                text = payload.get("text", "")
                                if isinstance(text, str):
                                    session["latest_partial_transcript"] = text
                            elif msg_type == "skip_phase":
                                # Skip phase no longer used — interview flows naturally
                                pass
                            elif msg_type == "coding_debrief_request":
                                raw_scoring = payload.get("scoring_json") or payload.get("scoring")
                                if isinstance(raw_scoring, dict):
                                    asyncio.create_task(
                                        _coding_debrief_flow(session, channel, raw_scoring)
                                    )
                    except Exception:
                        pass
                logger.debug("DataChannel message: %s", str(message)[:100])

        elif channel.label == "au-telemetry":
            session["au_channel"] = channel
            logger.info("AU telemetry channel opened")

            @channel.on("message")
            def on_au_message(message):
                if isinstance(message, (bytes, bytearray)):
                    au = parse_au_telemetry(message)
                    if au is not None:
                        session["latest_au"] = au
                        bh = session["blink_history"]
                        bh.append((au.timestamp, au.au45))
                        if len(bh) > 600:  # keep last 60s @ 10Hz
                            session["blink_history"] = bh[-600:]

    @pc.on("connectionstatechange")
    async def on_state_change():
        state = pc.connectionState
        logger.info("Session %s connection state: %s", session_id[:8], state)
        if state in ("failed", "closed"):
            await cleanup_session(session_id)

    offer = RTCSessionDescription(sdp=req.sdp, type=req.type)
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    logger.info("Session %s created (SDP exchange complete)", session_id[:8])

    return AnswerResponse(
        sdp=pc.localDescription.sdp,
        type=pc.localDescription.type,
        session_id=session_id,
    )


async def cleanup_session(session_id: str) -> None:
    """Clean up a WebRTC session."""
    session = _sessions.pop(session_id, None)
    if session is None:
        return
    task = session.get("audio_task")
    if task and not task.done():
        task.cancel()
    for task in list(session.get("transcribe_tasks", set())):
        if task and not task.done():
            task.cancel()
    pc = session.get("pc")
    if pc:
        await pc.close()
    logger.info("Session %s cleaned up", session_id[:8])
