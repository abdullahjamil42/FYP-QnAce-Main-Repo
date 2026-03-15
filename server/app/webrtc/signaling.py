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
import time
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
    "Welcome to your software interview. Please start with a short introduction: "
    "your background, your current role, and one project you are proud of."
)

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
    """Advance interview state and return the next software-themed prompt."""
    stage = session.get("interview_stage", "intro")
    idx = int(session.get("interview_question_idx", 0))

    if stage == "intro":
        session["interview_stage"] = "questions"
        if SOFTWARE_INTERVIEW_QUESTIONS:
            session["interview_question_idx"] = 1
            return f"Great introduction. First question: {SOFTWARE_INTERVIEW_QUESTIONS[0]}"
        return "Great introduction."

    if idx < len(SOFTWARE_INTERVIEW_QUESTIONS):
        session["interview_question_idx"] = idx + 1
        return f"Next question: {SOFTWARE_INTERVIEW_QUESTIONS[idx]}"

    return (
        "That concludes this software interview set. Nice work. "
        "If you want, we can start a new round focused on system design."
    )


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
        tts_result = await tts_eng.synthesize(chunk)
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
        send_status, send_transcript, send_scores, send_perception,
        parse_au_telemetry,
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
        "interview_stage": "intro",
        "interview_question_idx": 0,
        "interview_started": False,
        "latest_partial_transcript": "",
        "latest_transcript_text": "",
    }
    _sessions[session_id] = session

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
        dc = session.get("data_channel")
        loop = asyncio.get_running_loop()
        dur_s = len(audio_chunk) / 16_000
        t_pipeline_start = time.perf_counter()

        try:
            # 1-2-6. Run TQ + Vocal + RAG in parallel
            t_percept = time.perf_counter()
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
            blinks_per_min = 17.5  # default (real blink tracking needs Phase 5)
            # Map vocal emotion to positivity
            positive_emotions = {"confident", "composed", "engaged", "happy", "positive"}
            emotion_positivity = 0.7 if vocal_result.dominant_emotion in positive_emotions else 0.3

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
                "face_emotion": "neutral",  # face model not yet available
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

            # 7. Optional LLM feedback (Groq or Airforce) → TTS → Avatar
            llm_ttft_ms = 0.0
            classifier_ms = 0.0
            generator_ms = 0.0
            tts_first_ms = 0.0
            word_count = len(result.text.split())
            send_status(dc, f"interview: answer received ({word_count} words)")

            next_prompt = _next_interview_prompt(session)
            if next_prompt:
                from ..intelligence import interviewer as interviewer_intel

                current_question = str(session.get("current_question") or INTRO_QUESTION)
                interviewer_state = session.get("interviewer_state")
                conversation_history = session.get("interviewer_history") or []
                previous_modes = (interviewer_state or {}).get("last_modes", [])
                previous_mode = previous_modes[-1] if previous_modes else ""
                monologue_flag = bool(
                    word_count >= max(10, int(getattr(settings, "interview_interrupt_word_limit", 250)))
                )

                stream_state = {
                    "first_audio_ms": 0.0,
                    "total_duration_s": 0.0,
                    "chunks": 0,
                }

                async def _on_generator_sentence_chunk(sentence: str) -> None:
                    tts_eng = session.get("tts_engine")
                    tts_track = session.get("tts_track")
                    if tts_eng is None or tts_track is None:
                        return

                    from ..synthesis.tts import split_text_for_tts_streaming

                    max_chars = max(60, int(getattr(settings, "tts_chunk_max_chars", 150)))
                    chunks = split_text_for_tts_streaming(sentence, max_chars=max_chars)
                    if not chunks:
                        return

                    session["speaking"] = True
                    for chunk in chunks:
                        tts_result = await tts_eng.synthesize(chunk)
                        if tts_result.audio_pcm is None or len(tts_result.audio_pcm) == 0:
                            continue
                        tts_track.enqueue_audio(tts_result.audio_pcm, tts_result.sample_rate)
                        stream_state["chunks"] += 1
                        stream_state["total_duration_s"] += float(tts_result.duration_s)
                        if stream_state["first_audio_ms"] <= 0.0:
                            stream_state["first_audio_ms"] = (
                                (time.perf_counter() - t_pipeline_start) * 1000.0
                            )
                        rms = float(np.sqrt(np.mean(tts_result.audio_pcm.astype(np.float32) ** 2))) / 32768.0
                        session["audio_energy"] = rms

                turn_result = await interviewer_intel.generate_interviewer_turn(
                    transcript=result.text,
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
                    next_question=next_prompt,
                    settings=settings,
                    on_generator_sentence_chunk=_on_generator_sentence_chunk,
                )

                session["interviewer_state"] = turn_result.get("state")
                session["interviewer_history"] = turn_result.get("history", conversation_history)
                llm_ttft_ms = float(turn_result.get("llm_ttft_ms", 0.0))
                classifier_ms = float(turn_result.get("classifier_ms", 0.0))
                generator_ms = float(turn_result.get("generator_ms", 0.0))

                interviewer_text = str(turn_result.get("spoken_response") or next_prompt)
                mode = str(turn_result.get("mode") or "PROBE_GAP")
                evidence = str(turn_result.get("evidence") or "")
                streamed_chunk_count = int(turn_result.get("streamed_chunk_count", 0))
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
                if evidence:
                    send_status(dc, f"interview-evidence: {evidence[:140]}")

                send_status(dc, f"question: {interviewer_text[:180]}")
                if streamed_chunk_count > 0 and stream_state["chunks"] > 0:
                    tts_first_ms = float(stream_state["first_audio_ms"])
                    send_status(
                        dc,
                        (
                            "tts-streamed: "
                            f"chunks={stream_state['chunks']} "
                            f"duration={stream_state['total_duration_s']:.1f}s"
                        ),
                    )
                    if stream_state["total_duration_s"] > 0.0:
                        await asyncio.sleep(min(float(stream_state["total_duration_s"]), 2.0))
                    session["speaking"] = False
                    session["audio_energy"] = 0.0
                else:
                    tts_first_ms = await _speak_session_text(
                        session,
                        dc,
                        interviewer_text,
                        send_status,
                        t_pipeline_start,
                    )
                session["current_question"] = next_prompt

            # 8. Latency summary
            total_ms = (time.perf_counter() - t_pipeline_start) * 1000.0
            latency_report = (
                f"latency: percept={percept_ms:.0f}ms(tq={tq_ms:.0f}+vocal={vocal_ms:.0f}+rag={rag_ms:.0f}) "
                f"interviewer=cls:{classifier_ms:.0f}ms+gen:{generator_ms:.0f}ms "
                f"llm_ttft={llm_ttft_ms:.0f}ms "
                f"tts_first={tts_first_ms:.0f}ms total={total_ms:.0f}ms"
            )
            logger.info("Pipeline %s", latency_report)
            send_status(dc, latency_report)

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
                    asyncio.create_task(_post_transcript(result, current_chunk))
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

    def on_speech_end(audio_chunk):
        chunk = audio_chunk.copy()
        dur_s = len(chunk) / 16_000
        logger.info("on_speech_end fired: %.2fs audio", dur_s)
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
                send_status(channel, f"question: {INTRO_QUESTION}")
                asyncio.create_task(_speak_session_text(session, channel, INTRO_QUESTION, send_status))

            @channel.on("message")
            def on_message(message):
                if isinstance(message, str):
                    try:
                        import json

                        payload = json.loads(message)
                        if isinstance(payload, dict) and payload.get("type") == "partial_transcript":
                            text = payload.get("text", "")
                            if isinstance(text, str):
                                session["latest_partial_transcript"] = text
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
