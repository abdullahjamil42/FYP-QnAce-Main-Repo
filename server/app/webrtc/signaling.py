"""
Q&Ace — WebRTC Signaling (POST /offer → SDP answer).

- Receives browser SDP offer.
- Creates aiortc RTCPeerConnection.
- Sets up audio track consumption → VAD → STT pipeline.
- Returns SDP answer.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import time
import uuid
from typing import Any, Awaitable, Callable

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..intelligence.session_stages import (
    SessionStage, SessionTimer, QuestionBudget, SilenceMonitor,
    AcknowledgmentPicker, ThinkingDelay
)

logger = logging.getLogger("qace.signaling")
router = APIRouter()

# ── In-memory session store ──
_sessions: dict[str, dict[str, Any]] = {}
_semantic_detector: Any = None

SOFTWARE_INTERVIEW_QUESTIONS = [
    "Explain a backend system you built. What were the core components and trade-offs?",
    "Tell me about a production bug you diagnosed. How did you isolate and fix it?",
    "How do you design a REST API for reliability and versioning?",
    "Describe a time you improved application performance. What metrics moved?",
    "How would you design caching for a high-traffic read-heavy service?",
    "What testing strategy do you use across unit, integration, and end-to-end tests?",
    "Describe a difficult code review discussion and how you resolved it.",
    "If you had to scale this app to 10x users, what would you change first?",
]


def _next_interview_prompt(session: dict[str, Any]) -> str | None:
    """Advance interview state and return the next context-aware prompt."""
    stage = session.get("stage", SessionStage.SMALL_TALK)
    budget: QuestionBudget = session.get("question_budget")
    timer: SessionTimer = session.get("timer")
    cv_data = session.get("cv_data")
    
    questions = SOFTWARE_INTERVIEW_QUESTIONS
    if cv_data and "seed_bank" in cv_data and isinstance(cv_data["seed_bank"], list) and len(cv_data["seed_bank"]) > 0:
        questions = [q.get("question", "") for q in cv_data["seed_bank"] if q.get("question")]
        if not questions:
            questions = SOFTWARE_INTERVIEW_QUESTIONS

    if stage == SessionStage.SMALL_TALK:
        session["stage"] = SessionStage.INTRO
        if cv_data and cv_data.get("parsed_cv"):
            parsed = cv_data["parsed_cv"]
            name = parsed.get("name", "")
            roles = parsed.get("roles", [])
            role_ref = roles[0] if roles else "your recent work"
            name_ref = f", {name}" if name and str(name).lower() != "candidate" else ""
            return f"Great, let's get started. I was looking at your resume{name_ref}. Tell me a bit about your experience with {role_ref} and one project you are particularly proud of."
        return "Great, let's get started. Tell me a bit about your background, your current focus, and one project you are particularly proud of."

    elif stage == SessionStage.INTRO:
        session["stage"] = SessionStage.TECHNICAL
        timer.start()
        # Fall through to first technical question

    if stage == SessionStage.TECHNICAL:
        # Check if we should wrap up
        if budget.is_budget_exhausted() or timer.should_warn():
            session["stage"] = SessionStage.WRAP_UP
        else:
            idx = int(session.get("interview_question_idx", 0))
            if idx < len(questions):
                session["interview_question_idx"] = idx + 1
                
                # Fetch CV Anchor Context
                current_context = ""
                if cv_data and "seed_bank" in cv_data and idx < len(cv_data["seed_bank"]):
                    current_context = cv_data["seed_bank"][idx].get("cv_anchor", "")
                session["cv_context"] = current_context

                return questions[idx]
            else:
                session["stage"] = SessionStage.WRAP_UP
                
    if stage == SessionStage.WRAP_UP:
        session["stage"] = SessionStage.CLOSING
        return "Before we wrap up, do you have any questions for me about the role or the team?"
        
    if stage == SessionStage.CLOSING:
        session["stage"] = SessionStage.ENDED
        return None  # No more generated prompts, session will end
        
    return None


def _process_timer_events(
    session: dict[str, Any],
    channel: Any,
    *,
    send_time_warning_fn: Callable[[Any, int], None],
    send_session_ended_fn: Callable[[Any, str], None],
    send_stage_change_fn: Callable[[Any, str, dict | None], None],
    send_status_fn: Callable[[Any, str], None],
) -> bool:
    """Emit time-based events and return True when the session should end."""
    timer: SessionTimer | None = session.get("timer")
    if timer is None:
        return False

    if (
        timer._start_time is not None
        and not timer.is_expired()
        and timer.remaining_s() <= 300.0
        and not session.get("time_warning_sent", False)
    ):
        remaining_minutes = max(1, int(math.ceil(timer.remaining_s() / 60.0)))
        session["time_warning_sent"] = True
        send_time_warning_fn(channel, remaining_minutes)
        send_status_fn(channel, f"time-warning: {remaining_minutes}m remaining")

    if timer.is_expired():
        if not session.get("session_end_notified", False):
            session["session_end_notified"] = True
            session["stage"] = SessionStage.ENDED
            send_stage_change_fn(channel, SessionStage.ENDED.name, {"reason": "time_limit_reached"})
            send_session_ended_fn(channel, "time_limit_reached")
            send_status_fn(channel, "session-ended: time_limit_reached")
        return True

    return False


def _ensure_timer_started(session: dict[str, Any]) -> bool:
    """Start the session timer once; returns True when this call started it."""
    timer: SessionTimer | None = session.get("timer")
    if timer is None:
        return False

    already_started = timer._start_time is not None
    if not already_started:
        timer.start()
        return True
    return False


async def _run_session_timer_loop(
    session_id: str,
    session: dict[str, Any],
    sessions: dict[str, dict[str, Any]],
    *,
    process_timer_events_fn: Callable[[dict[str, Any], Any], bool],
    sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
    interval_s: float = 1.0,
    max_ticks: int | None = None,
) -> bool:
    """Drive periodic timer checks while a session is active.

    Returns True if the timer processing requested a session end, otherwise False.
    """
    ticks = 0
    while session_id in sessions:
        if max_ticks is not None and ticks >= max_ticks:
            return False

        await sleep_fn(interval_s)
        ticks += 1

        channel = session.get("data_channel")
        if not channel or getattr(channel, "readyState", "") != "open":
            continue

        if process_timer_events_fn(session, channel):
            return True

    return False


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
        tts_result = await tts_eng.synthesize(chunk, session.get("stress_level", "none"))
        if tts_result.audio_pcm is None or len(tts_result.audio_pcm) == 0:
            continue

        tts_track.enqueue_audio(tts_result.audio_pcm, tts_result.sample_rate)
        total_duration_s += float(tts_result.duration_s)

        if idx == 0:
            first_audio_ms = (time.perf_counter() - (started_at if started_at is not None else synth_t0)) * 1000.0

        rms = float(np.sqrt(np.mean(tts_result.audio_pcm.astype(np.float32) ** 2))) / 32768.0
        session["audio_energy"] = rms

    # Keep speaking state active briefly to drive avatar animation while queued audio plays.
    if total_duration_s > 0.0:
        send_status_fn(dc, f"tts: {total_duration_s:.1f}s via {getattr(tts_eng, 'engine_name', 'tts')}")
        await asyncio.sleep(min(total_duration_s, 2.0))

    session["speaking"] = False
    session["audio_energy"] = 0.0
    return first_audio_ms


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


def _audio_chunk_metrics(audio_chunk: np.ndarray) -> tuple[float, int, float]:
    """Return RMS, peak, and active-sample ratio for a 16kHz int16 chunk."""
    if audio_chunk is None or len(audio_chunk) == 0:
        return 0.0, 0, 0.0
    chunk_i32 = audio_chunk.astype(np.int32)
    abs_chunk = np.abs(chunk_i32)
    rms = float(np.sqrt(np.mean(chunk_i32.astype(np.float32) ** 2)))
    peak = int(abs_chunk.max()) if abs_chunk.size else 0
    active_ratio = float(np.mean(abs_chunk > 300))
    return rms, peak, active_ratio


def _normalize_transcript(text: str) -> str:
    """Normalize transcript text for robust phrase matching."""
    lowered = (text or "").strip().lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return " ".join(cleaned.split())


def _should_filter_silence_transcript(text: str, audio_chunk: np.ndarray) -> bool:
    """Filter common silence hallucinations from STT before pipeline fan-out."""
    normalized = _normalize_transcript(text)
    if not normalized:
        return True

    words = normalized.split()
    word_count = len(words)
    rms, peak, active_ratio = _audio_chunk_metrics(audio_chunk)

    silence_hallucinations = {
        "thank you",
        "thanks",
        "thankyou",
        "thank you very much",
        "you",
    }
    if normalized in silence_hallucinations and (rms < 1200.0 or active_ratio < 0.08):
        return True

    if word_count <= 3 and rms < 320.0 and peak < 2200 and active_ratio < 0.02:
        return True

    if word_count <= 2 and active_ratio < 0.01:
        return True

    return False

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
    duration_minutes: int = 20
    stress_level: str = "none"
    cv_session_id: str = ""


class AnswerResponse(BaseModel):
    sdp: str
    type: str = "answer"
    session_id: str


@router.post("/offer", response_model=AnswerResponse)
async def handle_offer(req: OfferRequest):
    """SDP offer → answer exchange. Sets up the full audio pipeline."""
    if not _AIORTC_AVAILABLE:
        raise HTTPException(503, "WebRTC runtime (aiortc) not available")

    from ..config import get_settings
    from ..models import registry
    from ..intelligence.rag import retrieve as rag_retrieve
    from ..intelligence.scoring import InterviewScoringEngine, RunningScorer, UtteranceScores
    from ..perception.stt import transcribe
    from ..perception.text_quality import classify_quality
    from ..perception.vocal import analyze as vocal_analyze
    from ..vad.ring_buffer import RingBuffer
    from ..vad.silero import EndOfSpeechDetector
    from ..webrtc.data_channel import (
        send_status, send_avatar_state, send_transcript, send_scores, send_perception,
        parse_au_telemetry,
        send_mic_gate, send_mic_reopen,
        send_stage_change, send_time_warning, send_session_ended, send_silence_prompt
    )
    from ..webrtc.tracks import consume_audio_track
    from ..webrtc.tracks import TTSAudioStreamTrack, AvatarVideoStreamTrack

    settings = get_settings()
    session_id = str(uuid.uuid4())
    pc = RTCPeerConnection()
    ring = RingBuffer(max_seconds=30.0, sample_rate=16_000)

    session: dict[str, Any] = {
        "id": session_id,
        "pc": pc,
        "ring": ring,
        "data_channel": None,
        "au_channel": None,
        "latest_au": None,
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
        "interview_started": False,
        "latest_partial_transcript": "",
        "latest_transcript_text": "",
        "last_filler_idx": -1,
        
        # Realism Engine Phase 1
        "stage": SessionStage.SMALL_TALK,
        "timer": SessionTimer(req.duration_minutes),
        "question_budget": QuestionBudget(req.duration_minutes),
        "silence_monitor": SilenceMonitor(),
        "ack_picker": AcknowledgmentPicker(),
        "thinking_delay": ThinkingDelay(),
        "time_warning_sent": False,
        "session_end_notified": False,
        
        # Phase 1 & 3: Stress and CV
        "stress_level": req.stress_level,
        "cv_session_id": req.cv_session_id,
    }
    _sessions[session_id] = session

    # Load CV data if present
    if req.cv_session_id:
        from ..webrtc.cv_routes import get_cv_session
        cv_data = get_cv_session(req.cv_session_id)
        if cv_data:
            session["cv_data"] = cv_data
            logger.info("Session %s loaded CV data and seed bank from session %s", session_id[:8], req.cv_session_id)

    # ── Outbound media tracks (server → client) ──
    tts_track = TTSAudioStreamTrack(output_rate=48_000)
    avatar_track = AvatarVideoStreamTrack(
        avatar_engine=session.get("avatar_engine"),
        session=session,
        fps=settings.avatar_fps,
    )
    session["tts_track"] = tts_track
    session["avatar_track"] = avatar_track
    pc.addTrack(tts_track)
    pc.addTrack(avatar_track)

    async def _post_transcript(result, audio_chunk):
        """Run scoring, perception, RAG, and optional LLM after a successful transcript."""
        import random
        dc = session.get("data_channel")
        loop = asyncio.get_running_loop()
        dur_s = len(audio_chunk) / 16_000
        t_pipeline_start = time.perf_counter()

        # 1. Gate the mic immediately
        send_mic_gate(dc, "turn_pipeline_started")

        # (Filler now handled in on_speech_end for absolute minimum latency)

        try:
            # 1. Eagerly dispatch Classifier task immediately (Problem 1 Fix)
            from ..intelligence import interviewer as interviewer_intel
            
            t_pipeline_start_parallel = time.perf_counter()
            current_question = str(session.get("current_question", ""))
            interviewer_state = session.get("interviewer_state")
            conversation_history = session.get("interviewer_history") or []
            previous_modes = (interviewer_state or {}).get("last_modes", [])
            previous_mode = previous_modes[-1] if previous_modes else ""
            
            word_count = len(result.text.split())
            monologue_limit = max(10, int(getattr(settings, "interview_interrupt_word_limit", 250)))
            monologue_flag = word_count >= monologue_limit

            classifier_fut = asyncio.create_task(interviewer_intel.classify_interviewer_turn(
                transcript=result.text,
                current_question=current_question,
                conversation_history=conversation_history,
                previous_mode=previous_mode,
                session_state=interviewer_state,
                monologue_flag=monologue_flag,
                settings=settings,
                stage=session.get("stage", SessionStage.SMALL_TALK).name,
            ))

            # 2. Launch perception tasks in parallel
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

            # 3. Wait for everything
            tq_result, vocal_result, rag_result, classifier_result = await asyncio.gather(
                tq_fut, vocal_fut, rag_fut, classifier_fut,
            )
            
            percept_ms = (time.perf_counter() - t_pipeline_start_parallel) * 1000.0
            classifier_ms = classifier_result.get("classifier_ms", 0.0)
            
            # 4. Process Scoring (remains sequential but now has all data)
            au = session.get("latest_au")
            eye_contact = au.eye_contact if au else 0.5
            positive_emotions = {"confident", "composed", "engaged", "happy", "positive"}
            emotion_positivity = 0.7 if vocal_result.dominant_emotion in positive_emotions else 0.3

            interview_scorer: InterviewScoringEngine = session.get("interview_scorer")
            telemetry = {
                "bert_classification": tq_result.label,
                "bert_base_score": tq_result.base_score,
                "llm_star_evaluation": tq_result.base_score,
                "whisper_wpm": result.wpm,
                "whisper_filler_count": result.filler_count,
                "whisper_word_count": word_count,
                "whisper_duration_s": dur_s,
                "wav2vec2_confidence": vocal_result.acoustic_confidence,
                "mediapipe_eye_contact": eye_contact,
                "mediapipe_bpm": 17.5,
                "action_units": [],
                "emotion_timeline": [],
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
                blink_deviation=0.0,
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

            # -- Adaptive Calibration (Phase 6) --
            comp_score = float(interview_scores["Sub_Scores"]["Composure"])
            if comp_score < 60.0:
                session["low_composure_count"] = session.get("low_composure_count", 0) + 1
            else:
                session["low_composure_count"] = 0

            lower_text = result.text.lower()
            needs_pause = any(phr in lower_text for phr in ["slow down", "need a moment", "can we pause", "give me a second"])
            current_stress = session.get("stress_level", "none")
            
            if needs_pause:
                send_status(dc, "adaptive-calibration: candidate requested pause, adding 3s delay")
                await asyncio.sleep(3.0)
                
            if session.get("low_composure_count", 0) >= 2 and current_stress in ("brutal", "high"):
                new_stress = "high" if current_stress == "brutal" else "mild"
                session["stress_level"] = new_stress
                session["low_composure_count"] = 0
                send_status(dc, f"adaptive-calibration: downgraded stress to {new_stress}")

            # 5. Send Perception/Status
            send_perception(dc, {
                "vocal_emotion": vocal_result.dominant_emotion,
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
                send_status(dc, f"rag: {len(rag_result.passages)} passages in {rag_result.retrieval_ms:.0f}ms")

            # 7. Optional LLM feedback (Groq or Airforce) → TTS → Avatar
            llm_ttft_ms = 0.0
            generator_ms = 0.0
            tts_first_ms = 0.0
            send_status(dc, f"interview: answer received ({word_count} words)")

            next_prompt = _next_interview_prompt(session)
            if next_prompt:
                if classifier_result.get("mode") == "DEAD_SILENCE":
                    import random
                    send_avatar_state(dc, "AVATAR_COLD")
                    send_status(dc, "stress: dead silence inserted")
                    await asyncio.sleep(random.uniform(4.0, 6.0))
                    
                # Decide on acknowledgment phrase and thinking delay
                ack_phrase = ""
                if session.get("stage") not in (SessionStage.SMALL_TALK, SessionStage.CLOSING):
                    picker: AcknowledgmentPicker = session.get("ack_picker")
                    if picker and session.get("stress_level", "none") not in ("high", "brutal"):
                        ack_phrase = picker.pick() + " "
                        
                delay_calculator: ThinkingDelay = session.get("thinking_delay")
                thinking_delay_s = delay_calculator.get_delay_s(word_count, session.get("stress_level", "none")) if delay_calculator else 1.2
                
                stream_state = {
                    "first_audio_ms": 0.0,
                    "total_duration_s": 0.0,
                    "chunks": 0,
                }

                async def _on_chunk(sentence: str) -> None:
                    tts_eng = session.get("tts_engine")
                    if not tts_eng or not tts_track: return
                    from ..synthesis.tts import split_text_for_tts_streaming
                    max_chars = max(60, int(getattr(settings, "tts_chunk_max_chars", 150)))
                    
                    if stream_state["chunks"] == 0 and ack_phrase:
                        sentence = ack_phrase + sentence
                        
                    chunks = split_text_for_tts_streaming(sentence, max_chars=max_chars)
                    
                    for chunk in chunks:
                        res = await tts_eng.synthesize(chunk, session.get("stress_level", "none"))
                        if res.audio_pcm is not None and len(res.audio_pcm) > 0:
                            if stream_state["chunks"] == 0:
                                # Apply thinking delay before first actual audio buffering
                                send_status(dc, f"thinking-delay: {thinking_delay_s:.1f}s")
                                await asyncio.sleep(thinking_delay_s)
                            
                            tts_track.enqueue_audio(res.audio_pcm, res.sample_rate)
                            stream_state["chunks"] += 1
                            stream_state["total_duration_s"] += float(res.duration_s)
                            if stream_state["first_audio_ms"] <= 0.0:
                                stream_state["first_audio_ms"] = (time.perf_counter() - t_pipeline_start) * 1000.0
                            session["audio_energy"] = float(np.sqrt(np.mean(res.audio_pcm.astype(np.float32) ** 2))) / 32768.0

                # 6. Generator Phase (Sequential to classifier but has all perception data)
                turn_result = await interviewer_intel.generate_interviewer_response(
                    transcript=result.text,
                    current_question=current_question,
                    classifier_result=classifier_result,
                    ideal_answer_rubric=rubric_context,
                    rag_passages=list(rag_result.passages or []),
                    rag_distances=list(rag_result.distances or []),
                    vocal_confidence=float(vocal_result.acoustic_confidence),
                    text_quality_score=float(tq_result.base_score),
                    text_quality_label=str(tq_result.label),
                    conversation_history=conversation_history,
                    session_state=interviewer_state,
                    next_question=next_prompt,
                    settings=settings,
                    on_generator_sentence_chunk=_on_chunk,
                    stress_level=session.get("stress_level", "none"),
                    cv_context=session.get("cv_context", ""),
                )

                session["interviewer_state"] = turn_result.get("state")
                session["interviewer_history"] = turn_result.get("history")
                session["current_question"] = next_prompt
                
                llm_ttft_ms = float(turn_result.get("llm_ttft_ms", 0.0))
                generator_ms = float(turn_result.get("generator_ms", 0.0))
                tts_first_ms = float(stream_state["first_audio_ms"]) if stream_state["first_audio_ms"] > 0 else 0.0
            elif session.get("stage") == SessionStage.ENDED and not session.get("session_end_notified", False):
                session["session_end_notified"] = True
                send_stage_change(dc, SessionStage.ENDED.name, {"reason": "interview_complete"})
                send_session_ended(dc, "interview_complete")
                send_status(dc, "session-ended: interview_complete")

            total_ms = (time.perf_counter() - t_pipeline_start) * 1000.0
            latency_report = (
                f"latency: total={total_ms:.0f}ms "
                f"percept={percept_ms:.0f}ms cls={classifier_ms:.0f}ms gen={generator_ms:.0f}ms "
                f"tts_first={tts_first_ms:.0f}ms"
            )
            logger.info("Pipeline %s", latency_report)
            send_status(dc, latency_report)
            
            # Final Drain and Reopen
            if tts_track:
                await tts_track.wait_until_drained()
            session["speaking"] = False
            session["audio_energy"] = 0.0
            
            # Restart silence monitor after AI finishes speaking
            if "silence_monitor" in session:
                session["silence_monitor"].activate()
                
            send_mic_reopen(dc, "interviewer_finished_speaking")


        except Exception as exc:
                logger.exception("Post-transcript pipeline failed: %s", exc)
                send_status(dc, f"pipeline-error: {exc}")
                send_mic_reopen(dc, "pipeline_error_recovery")

    async def transcribe_and_send(audio_chunk):
        """Run final STT off the event loop, then send one stable transcript."""
        needs_mic_reopen = True
        try:
            dc = session.get("data_channel")
            dur_s = len(audio_chunk) / 16_000
            send_status(dc, f"transcribing {dur_s:.1f}s audio…")
            loop = asyncio.get_running_loop()
            current_chunk = audio_chunk
            while current_chunk is not None:
                model = session.get("stt_model") or registry.whisper_model
                model_device = session.get("stt_device") or getattr(registry, "whisper_model_device", None)
                chunk_duration_s = len(current_chunk) / 16_000
                timeout_s = max(15.0, chunk_duration_s * 4.0)

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
                    if _should_filter_silence_transcript(result.text, current_chunk):
                        rms, peak, active_ratio = _audio_chunk_metrics(current_chunk)
                        send_status(
                            dc,
                            (
                                "stt-filtered: suppressed low-energy transcript "
                                f"rms={rms:.0f} peak={peak} active={active_ratio:.2f}"
                            ),
                        )
                    else:
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
                        asyncio.create_task(_post_transcript(result, current_chunk))
                        needs_mic_reopen = False
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
                return

            if needs_mic_reopen:
                dc = session.get("data_channel")
                if "silence_monitor" in session:
                    session["silence_monitor"].activate()
                send_mic_reopen(dc, "no_valid_transcript")

    def inject_filler():
        """Pick a random filler from cache and enqueue immediately."""
        import random
        tts_track = session.get("tts_track")
        if tts_track and getattr(registry, "filler_cache", None):
            available = list(range(len(registry.filler_cache)))
            last_idx = session.get("last_filler_idx", -1)
            if last_idx in available and len(available) > 1:
                available.remove(last_idx)
            
            filler_idx = random.choice(available)
            session["last_filler_idx"] = filler_idx
            filler_pcm = registry.filler_cache[filler_idx]
            
            # Wake up speaking state for avatar
            session["speaking"] = True
            tts_track.enqueue_audio(filler_pcm, 24_000)
            logger.info("Early filler audio injected in on_speech_end (idx=%d)", filler_idx)

    def on_speech_start():
        if "silence_monitor" in session:
            session["silence_monitor"].deactivate()

    def on_speech_end(audio_chunk):
        chunk = audio_chunk.copy()
        dur_s = len(chunk) / 16_000
        logger.info("on_speech_end fired: %.2fs audio", dur_s)
        dc = session.get("data_channel")
        
        # Interruption Engine Phase 4 Check
        if session.get("interrupt_fired_this_turn"):
            session["interrupt_fired_this_turn"] = False
            send_status(dc, "Speech end skipped due to mid-utterance interruption")
            return

        send_status(dc, f"speech-end detected ({dur_s:.1f}s)")
        send_mic_gate(dc, "speech_end_detected")

        # Optional early filler can help perceived responsiveness, but is
        # disabled by default to avoid acoustic loopback into STT.
        if bool(getattr(settings, "tts_enable_early_filler", False)):
            inject_filler()

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
                
                async def _start_interview():
                    try:
                        logger.info("Session %s: _start_interview triggered. Waiting for connectionState...", session_id[:8])
                        # Wait up to 3 seconds for peer connection to establish media paths
                        for _ in range(30):
                            if pc.connectionState == "connected":
                                break
                            await asyncio.sleep(0.1)
                            
                        logger.info("Session %s: PC state is %s. Generating opener...", session_id[:8], pc.connectionState)
                        await asyncio.sleep(0.5)  # extra buffer for browser media pipeline
                        
                        from ..intelligence import interviewer as interviewer_intel
                        _ensure_timer_started(session)
                        send_stage_change(channel, SessionStage.SMALL_TALK.name)
                        opener = await interviewer_intel.generate_small_talk_opener(settings)
                        logger.info("Session %s: Opener generated: %s", session_id[:8], opener)
                        session["current_question"] = opener
                        send_status(channel, f"question: {opener}")
                        
                        logger.info("Session %s: Calling _speak_session_text...", session_id[:8])
                        await _speak_session_text(session, channel, opener, send_status)
                        logger.info("Session %s: Finished speaking opener.", session_id[:8])
                        
                        if "silence_monitor" in session:
                            session["silence_monitor"].activate()
                    except Exception as exc:
                        logger.error("Failed to start interview: %s", exc)

                asyncio.create_task(_start_interview())

                async def _silence_loop():
                    from ..intelligence import interviewer as interviewer_intel
                    while session_id in _sessions:
                        await asyncio.sleep(1.0)
                        dc = session.get("data_channel")
                        if not dc or getattr(dc, "readyState", "") != "open":
                            continue
                        monitor: SilenceMonitor = session.get("silence_monitor")
                        if not monitor or session.get("speaking") or session.get("transcribe_running"):
                            continue
                        if session.get("stage") not in (SessionStage.TECHNICAL, SessionStage.WRAP_UP):
                            continue

                        level = monitor.check_silence()
                        if level == 1:
                            send_silence_prompt(dc, "Take your time.")
                        elif level == 2:
                            send_silence_prompt(dc, "Let me put it another way...")
                            rephrase = await interviewer_intel.generate_rephrased_question(
                                session.get("current_question", ""), settings
                            )
                            session["current_question"] = rephrase
                            await _speak_session_text(session, dc, rephrase, send_status)
                            monitor.activate()
                        elif level == 3:
                            send_silence_prompt(dc, "Moving on...")
                            budget: QuestionBudget = session.get("question_budget")
                            if budget:
                                budget.complete_topic()
                            next_q = _next_interview_prompt(session)
                            if next_q:
                                session["current_question"] = next_q
                                await _speak_session_text(session, dc, "No worries, let's come back to that. " + next_q, send_status)
                                monitor.activate()

                asyncio.create_task(_silence_loop())

                async def _timer_loop():
                    await _run_session_timer_loop(
                        session_id,
                        session,
                        _sessions,
                        process_timer_events_fn=lambda current_session, dc: _process_timer_events(
                            current_session,
                            dc,
                            send_time_warning_fn=send_time_warning,
                            send_session_ended_fn=send_session_ended,
                            send_stage_change_fn=send_stage_change,
                            send_status_fn=send_status,
                        ),
                    )

                asyncio.create_task(_timer_loop())

            @channel.on("message")
            def on_message(message):
                if isinstance(message, str):
                    try:
                        import json
                        import random

                        payload = json.loads(message)
                        if isinstance(payload, dict) and payload.get("type") == "partial_transcript":
                            text = payload.get("text", "")
                            if isinstance(text, str):
                                session["latest_partial_transcript"] = text
                                
                                # Interruption Engine Phase 4
                                stress_level = session.get("stress_level", "none")
                                if stress_level in ("high", "brutal") and not session.get("interrupt_fired_this_turn"):
                                    word_count = len(text.split())
                                    threshold = 20 if stress_level == "brutal" else 35
                                    prob = 0.3 if stress_level == "brutal" else 0.15
                                    
                                    if word_count > threshold and random.random() < prob:
                                        session["interrupt_fired_this_turn"] = True
                                        
                                        async def trigger_interruption(text_snippet):
                                            send_avatar_state(channel, "AVATAR_INTERRUPT")
                                            # Generate text
                                            import time
                                            from ..intelligence import interviewer as interviewer_intel
                                            from ..config import get_settings
                                            
                                            _settings = get_settings()
                                            send_status(channel, "stress: interruption triggered")
                                            
                                            # Minimal fallback interrupt text locally if LLM takes too long
                                            spoken_response = "Let me stop you right there. Bottom line?" if stress_level == "brutal" else "Hang on, let's pivot for a second. What's the main takeaway?"
                                            
                                            # Fire TTS
                                            tts_eng = session.get("tts_engine")
                                            tts_track = session.get("tts_track")
                                            if tts_eng and tts_track:
                                                res = await tts_eng.synthesize(spoken_response, stress_level)
                                                if res.audio_pcm is not None:
                                                    tts_track.enqueue_audio(res.audio_pcm, res.sample_rate)
                                                    # Mic gate 300ms later to allow overlap
                                                    await asyncio.sleep(0.3)
                                                    send_mic_gate(channel, "interrupted by interviewer")
                                                    session["speaking"] = True
                                                    await asyncio.sleep(res.duration_s)
                                                    session["speaking"] = False
                                                    send_mic_reopen(channel, "interruption_finished")
                                                    
                                        asyncio.create_task(trigger_interruption(text))
                                
                    except Exception as exc:
                        logger.warning(f"Error in on_message: {exc}")

        elif channel.label == "au-telemetry":
            session["au_channel"] = channel
            logger.info("AU telemetry channel opened")

            @channel.on("message")
            def on_au_message(message):
                if isinstance(message, (bytes, bytearray)):
                    au = parse_au_telemetry(message)
                    if au is not None:
                        session["latest_au"] = au

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
