"""
Q&Ace — Coaching endpoint.

POST /coaching/generate
  - Accepts session summary data (scores, transcripts, mode, difficulty).
  - If QACE_LLM_PROVIDER=local, swaps the local LLM server to the coach
    adapter, streams coaching output, then swaps back to evaluator.
  - If Groq/Airforce, calls the cloud API with a coaching system prompt.
  - Returns an SSE stream of text chunks.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Optional

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .auth import require_user
from .config import get_settings
from .intelligence.llm import resolve_provider_config, stream_llm, swap_adapter
from .personalization import (
    build_student_context,
    get_or_create_conversation,
    insert_message,
    maybe_refresh_summary,
)

logger = logging.getLogger("qace.coaching")

router = APIRouter()

COACHING_SYSTEM_PROMPT = """\
You are Q&Ace's post-interview personal coach. After a mock interview session, \
you help the candidate strengthen their weak areas through targeted feedback. \
You're a warm mentor: direct about gaps, generous about wins, and you address \
the candidate by their first name when you know it.

Your coaching style:
- Clear and structured — use short sections with bold headers
- Encouraging but honest — address gaps directly without being harsh
- Practical — every piece of content should help the candidate perform better next time
- Personal — when you know the candidate's name and history, weave it in naturally \
  ("Aziq, your delivery is up from last time — the gap now is structure")

You will receive session data including scores, interview mode, difficulty, \
and a transcript of what the candidate said. Generate a personalized coaching \
report with the following sections:

**Session Overview** — 2 sentences summarising how the interview went.
**Key Strengths** — 2-3 bullet points on what went well (be specific).
**Areas to Improve** — 2-3 bullet points on concrete weaknesses found in the transcript.
**Drill Plan** — 3 numbered action steps the candidate should practice before their next interview.

Keep the total response under 250 words. Be direct and specific, not generic.
"""


class CoachingRequest(BaseModel):
    mode: str = "technical"
    difficulty: str = "standard"
    duration_minutes: int = 20
    content_score: float = 0.0
    delivery_score: float = 0.0
    composure_score: float = 0.0
    final_score: float = 0.0
    transcript_texts: list[str] = []
    vocal_emotion: str = "neutral"
    face_emotion: str = "neutral"
    session_id: Optional[str] = None


async def _stream_coaching(
    request: CoachingRequest,
    user_id: Optional[str],
) -> AsyncIterator[str]:
    settings = get_settings()
    provider = resolve_provider_config(settings)

    if provider is None:
        yield "data: [LLM not configured — set GROQ_API_KEY or start the local LLM server]\n\n"
        return

    is_local = provider.provider == "local"

    student_context = await build_student_context(user_id)
    system_prompt = COACHING_SYSTEM_PROMPT + student_context

    conversation_id: str | None = None
    if user_id and request.session_id:
        conversation_id = await get_or_create_conversation(
            user_id, "coaching", session_id=request.session_id
        )

    # Build the user message from session data
    transcript_summary = "\n".join(
        f"- {t}" for t in request.transcript_texts[-10:] if t.strip()
    ) or "(no transcript available)"

    user_message = (
        f"Interview mode: {request.mode} | Difficulty: {request.difficulty} | "
        f"Duration: {request.duration_minutes} minutes\n\n"
        f"Scores:\n"
        f"  - Content Quality: {request.content_score:.0f}/100\n"
        f"  - Delivery: {request.delivery_score:.0f}/100\n"
        f"  - Composure: {request.composure_score:.0f}/100\n"
        f"  - Overall: {request.final_score:.0f}/100\n\n"
        f"Perception signals:\n"
        f"  - Vocal emotion: {request.vocal_emotion}\n"
        f"  - Facial emotion: {request.face_emotion}\n\n"
        f"Candidate transcript excerpts:\n{transcript_summary}"
    )

    # Swap to coach adapter for local LLM
    if is_local:
        await swap_adapter("coach")

    assistant_chunks: list[str] = []
    try:
        async for token in stream_llm(
            transcript=user_message,
            system_prompt=system_prompt,
            provider_config=provider,
            temperature=0.6,
            max_tokens=350,
        ):
            assistant_chunks.append(token)
            # SSE format
            safe = token.replace("\n", "\\n")
            yield f"data: {safe}\n\n"
    finally:
        # Always swap back to evaluator so the next interview is ready
        if is_local:
            await swap_adapter("evaluator")

    if conversation_id:
        full = "".join(assistant_chunks).strip()
        if full:
            await insert_message(conversation_id, "user", user_message)
            await insert_message(conversation_id, "assistant", full)
        if user_id:
            import asyncio
            asyncio.create_task(
                maybe_refresh_summary(user_id, conversation_id=conversation_id, force=True)
            )

    yield "data: [DONE]\n\n"


@router.post("/generate")
async def generate_coaching(
    request: CoachingRequest,
    user_id: Optional[str] = Depends(require_user),
) -> StreamingResponse:
    """
    Stream AI coaching feedback for a completed interview session.

    The response is a Server-Sent Events stream. Each event contains a text
    chunk. The final event is `data: [DONE]`.
    """
    return StreamingResponse(
        _stream_coaching(request, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
