"""
Q&Ace — DataChannel handler (server side).

Handles:
  - Outbound: transcript, scores, perception, status events → client
  - Inbound: AU telemetry binary packets from client (10Hz, unreliable)

Per ADR-010: AU telemetry uses RTCDataChannel with ordered=false, maxRetransmits=0.
Transcripts / scores use a reliable ordered channel created by the client.
"""

from __future__ import annotations

import json
import logging
import struct
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger("qace.datachannel")


@dataclass
class AUTelemetry:
    """Latest Action Unit values from client MediaPipe."""
    timestamp: int = 0
    au4: float = 0.0   # brow lowerer
    au12: float = 0.0   # lip corner puller
    au45: float = 0.0   # blink
    eye_contact: float = 0.0


def send_event(channel: Any, event_type: str, data: dict | None = None) -> None:
    """Send a JSON event over the data channel if it's open."""
    if channel is None:
        return
    try:
        if hasattr(channel, "readyState") and channel.readyState != "open":
            return
        payload = json.dumps({"type": event_type, **(data or {})})
        channel.send(payload)
    except Exception as exc:
        logger.warning("DataChannel send error (%s): %s", event_type, exc)


def send_transcript(channel: Any, text: str, inference_ms: float, wpm: float, fillers: int) -> None:
    """Send a transcript result to the client."""
    send_event(channel, "transcript", {
        "text": text,
        "inference_ms": round(inference_ms, 1),
        "wpm": round(wpm, 1),
        "filler_count": fillers,
    })


def send_scores(channel: Any, scores: dict) -> None:
    """Send per-utterance and running-average scores."""
    send_event(channel, "scores", scores)


def send_perception(channel: Any, perception_data: dict) -> None:
    """Send perception analysis results (vocal, face, text quality)."""
    send_event(channel, "perception", perception_data)


def send_status(channel: Any, status: str) -> None:
    """Send a system status event (e.g. 'audio-track-received')."""
    send_event(channel, "status", {"message": status})


def send_phase(channel: Any, phase: str, duration_s: float = 0.0) -> None:
    """Send an interview phase event (thinking / answering / transition)."""
    send_event(channel, "phase", {"phase": phase, "duration_s": duration_s})


def send_question(
    channel: Any,
    text: str,
    index: int,
    total: int,
    question_type: str = "role_specific",
    voice: str = "male",
) -> None:
    """Send the current interview question to the client."""
    send_event(channel, "question", {
        "text": text,
        "index": index,
        "total": total,
        "question_type": question_type,
        "voice": voice,
    })


def send_interview_end(
    channel: Any,
    total_questions: int,
    answered: int,
    skipped: int,
    per_question_scores: list | None = None,
    avg_total_score: float = 0.0,
) -> None:
    """Notify the client that the interview is complete."""
    send_event(channel, "interview_end", {
        "total_questions": total_questions,
        "answered": answered,
        "skipped": skipped,
        "per_question_scores": per_question_scores or [],
        "avg_total_score": avg_total_score,
    })


def send_answer_complete(
    channel: Any,
    completeness_score: float,
    signals: dict,
) -> None:
    """Notify the client that an answer has been deemed complete."""
    send_event(channel, "answer_complete", {
        "completeness_score": round(completeness_score, 3),
        "signals": signals,
    })


def parse_au_telemetry(data: bytes) -> Optional[AUTelemetry]:
    """
    Parse binary AU telemetry packet (20 bytes).
    Format: [timestamp:uint32][AU4:f32][AU12:f32][AU45:f32][eye_contact:f32]
    """
    if len(data) < 20:
        return None
    try:
        ts, au4, au12, au45, eye = struct.unpack("<Iffff", data[:20])
        return AUTelemetry(
            timestamp=ts,
            au4=au4,
            au12=au12,
            au45=au45,
            eye_contact=eye,
        )
    except struct.error:
        return None
