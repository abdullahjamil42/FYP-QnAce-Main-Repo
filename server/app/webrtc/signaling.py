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
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("qace.signaling")
router = APIRouter()

# ── In-memory session store ──
_sessions: dict[str, dict[str, Any]] = {}


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
    from ..intelligence.scoring import RunningScorer, compute_utterance_scores
    from ..intelligence.llm import build_system_prompt, resolve_provider_config, stream_llm
    from ..perception.stt import transcribe
    from ..perception.text_quality import classify_quality
    from ..perception.vocal import analyze as vocal_analyze
    from ..synthesis.punctuation_buffer import PunctuationBuffer
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
        # Phase 4 synthesis state
        "tts_engine": getattr(registry, "tts_engine", None),
        "avatar_engine": getattr(registry, "avatar_engine", None),
        "speaking": False,
        "audio_energy": 0.0,
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
            rag_ms = percept_ms  # wall-clock for the parallel group

            # 3. AU telemetry snapshot
            au = session.get("latest_au")
            eye_contact = au.eye_contact if au else 0.5
            blinks_per_min = 17.5  # default (real blink tracking needs Phase 5)
            # Map vocal emotion to positivity
            positive_emotions = {"confident", "composed", "engaged", "happy", "positive"}
            emotion_positivity = 0.7 if vocal_result.dominant_emotion in positive_emotions else 0.3

            # 4. Compute scores
            scores = compute_utterance_scores(
                text_quality_score=tq_result.base_score,
                wpm=result.wpm,
                filler_count=result.filler_count,
                duration_s=dur_s,
                vocal_confidence=vocal_result.acoustic_confidence,
                eye_contact_ratio=eye_contact,
                blinks_per_min=blinks_per_min,
                emotion_positivity=emotion_positivity,
            )

            session["scorer"].add(scores)
            send_scores(dc, session["scorer"].to_dict())
            send_status(dc, f"scores: {scores.final:.1f}/100")

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
                send_status(dc, f"rag: {len(rag_result.passages)} passages in {percept_ms:.0f}ms")

            # 7. Optional LLM feedback (Groq or Airforce) → TTS → Avatar
            provider_config = resolve_provider_config(settings)
            llm_ttft_ms = 0.0
            tts_first_ms = 0.0

            async def _speak_feedback_text(feedback_text: str, started_at: float | None = None) -> None:
                nonlocal tts_first_ms
                tts_eng = session.get("tts_engine")
                tts_track = session.get("tts_track")
                if tts_eng is None or tts_track is None:
                    return
                t0 = time.perf_counter()
                tts_result = await tts_eng.synthesize(feedback_text)
                elapsed_ms = (time.perf_counter() - (started_at if started_at is not None else t0)) * 1000.0
                if tts_first_ms == 0.0:
                    tts_first_ms = elapsed_ms
                if tts_result.audio_pcm is not None and len(tts_result.audio_pcm) > 0:
                    tts_track.enqueue_audio(tts_result.audio_pcm, tts_result.sample_rate)
                    rms = float(np.sqrt(np.mean(tts_result.audio_pcm.astype(np.float32) ** 2))) / 32768.0
                    session["speaking"] = True
                    session["audio_energy"] = rms
                    send_status(dc, f"tts: {tts_result.duration_s:.1f}s via {tts_result.engine_name}")
                    await asyncio.sleep(min(tts_result.duration_s, 2.0))
                session["speaking"] = False
                session["audio_energy"] = 0.0

            if provider_config:
                send_status(dc, "generating feedback…")
                system_prompt = build_system_prompt(
                    rubric_context=rubric_context,
                    vocal_emotion=vocal_result.dominant_emotion,
                    acoustic_confidence=vocal_result.acoustic_confidence,
                    face_emotion="neutral",
                    text_quality_label=tq_result.label,
                    text_quality_score=tq_result.base_score,
                    wpm=result.wpm,
                    filler_count=result.filler_count,
                )
                feedback_chunks: list[str] = []
                tts_text_queue: asyncio.Queue[str | None] = asyncio.Queue()
                t_llm_start = time.perf_counter()
                llm_first_token_seen = False
                tts_first_audio_seen = False
                llm_error_text: str | None = None

                def on_llm_chunk(chunk: str):
                    nonlocal llm_ttft_ms, llm_first_token_seen, llm_error_text
                    text = chunk.strip()
                    if not llm_first_token_seen:
                        llm_ttft_ms = (time.perf_counter() - t_llm_start) * 1000.0
                        llm_first_token_seen = True
                    if not feedback_chunks and _is_unusable_llm_feedback(text):
                        llm_error_text = text
                        return
                    feedback_chunks.append(chunk)
                    send_status(dc, f"llm-{provider_config.provider}-chunk: {chunk[:80]}")
                    tts_text_queue.put_nowait(chunk)

                tts_track = session.get("tts_track")
                tts_eng = session.get("tts_engine")

                async def _tts_consumer():
                    nonlocal tts_first_ms, tts_first_audio_seen
                    while True:
                        text = await tts_text_queue.get()
                        if text is None:
                            break
                        if tts_eng is None:
                            continue
                        # Drain additional queued chunks to batch them
                        # into a single TTS call (reduces HTTP roundtrips)
                        parts = [text]
                        while not tts_text_queue.empty():
                            extra = tts_text_queue.get_nowait()
                            if extra is None:
                                break
                            parts.append(extra)
                        else:
                            extra = None  # didn't hit sentinel
                        batch_text = " ".join(parts)
                        try:
                            tts_result = await tts_eng.synthesize(batch_text)
                            if tts_result.audio_pcm is not None and len(tts_result.audio_pcm) > 0:
                                if not tts_first_audio_seen:
                                    tts_first_ms = (time.perf_counter() - t_llm_start) * 1000.0
                                    tts_first_audio_seen = True
                                if tts_track is not None:
                                    tts_track.enqueue_audio(tts_result.audio_pcm, tts_result.sample_rate)
                                rms = float(np.sqrt(np.mean(
                                    tts_result.audio_pcm.astype(np.float32) ** 2
                                ))) / 32768.0
                                session["speaking"] = True
                                session["audio_energy"] = rms
                                send_status(dc, f"tts: {tts_result.duration_s:.1f}s via {tts_result.engine_name}")
                        except Exception as tts_exc:
                            logger.warning("TTS synthesis error: %s", tts_exc)
                        if extra is None:
                            break  # sentinel was consumed
                    session["speaking"] = False
                    session["audio_energy"] = 0.0
                    if tts_track is not None:
                        tts_track.finish()

                consumer_task = asyncio.create_task(_tts_consumer())

                buf = PunctuationBuffer(on_chunk=on_llm_chunk)
                async for token in stream_llm(result.text, system_prompt, provider_config):
                    buf.feed(token)
                buf.flush()
                tts_text_queue.put_nowait(None)
                await consumer_task

                full_feedback = "".join(feedback_chunks).strip()
                if llm_error_text or not full_feedback:
                    if llm_error_text:
                        logger.warning(
                            "LLM provider %s returned unusable feedback: %s",
                            provider_config.provider,
                            llm_error_text[:120],
                        )
                        send_status(dc, f"llm-{provider_config.provider}-fallback: {llm_error_text[:80]}")
                    fallback_feedback = _build_fallback_feedback(
                        transcript=result.text,
                        text_quality_label=tq_result.label,
                        filler_count=result.filler_count,
                        wpm=result.wpm,
                    )
                    send_status(dc, f"feedback: {fallback_feedback[:120]}")
                    await _speak_feedback_text(fallback_feedback, t_llm_start)
                else:
                    send_status(dc, f"feedback: {full_feedback[:120]}")
            else:
                send_status(dc, "llm: no configured Groq or Airforce API key — using local fallback feedback")
                fallback_feedback = _build_fallback_feedback(
                    transcript=result.text,
                    text_quality_label=tq_result.label,
                    filler_count=result.filler_count,
                    wpm=result.wpm,
                )
                send_status(dc, f"feedback: {fallback_feedback[:120]}")
                await _speak_feedback_text(fallback_feedback)

            # 8. Latency summary
            total_ms = (time.perf_counter() - t_pipeline_start) * 1000.0
            latency_report = (
                f"latency: percept={percept_ms:.0f}ms(tq={tq_ms:.0f}+vocal={vocal_ms:.0f}+rag) "
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

            @channel.on("message")
            def on_message(message):
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
