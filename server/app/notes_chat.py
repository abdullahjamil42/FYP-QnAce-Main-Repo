"""
Q&Ace — Notes Chat endpoint.

POST /notes/chat
  - Topic-scoped study assistant for the Study Notes page.
  - Receives the current topic, section, an excerpt of the visible note,
    a short conversation history, and the user's new message.
  - Streams the assistant reply via SSE using the same provider
    infrastructure as /coaching/generate.
  - No adapter swap: keeps the default ``evaluator`` adapter to avoid
    races with concurrent coaching streams.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .auth import require_user
from .config import get_settings
from .intelligence.llm import resolve_provider_config, stream_llm
from .personalization import (
    build_student_context,
    fetch_history_for_user,
    fetch_recent_messages,
    get_or_create_conversation,
    insert_message,
    maybe_refresh_summary,
)

logger = logging.getLogger("qace.notes_chat")

router = APIRouter()

NOTES_CHAT_SYSTEM_PROMPT = """\
You are Q&Ace's Study Notes tutor — the student's personal mentor. \
Warm, encouraging, honest. You greet the student by their first name on \
the very first turn of a conversation (and only then), and you weave in \
what you know about their progress when it's genuinely relevant — not as \
a recital. The student is reading a specific section of their notes \
(shown below) and chatting with you about it.

Your job is to TEACH, not to recite the notes. The student already has the \
notes in front of them. They're talking to you because they want a thinking \
partner who can:
- Explain ideas in plain language with concrete examples and analogies
- Add intuition and "why does this matter" context
- Connect concepts the notes only mention briefly
- Answer follow-up questions the notes don't cover directly
- Bring in your own world knowledge to make ideas click

Use the note excerpt as your ANCHOR — it tells you what topic the student is \
on right now. Stay aligned with that topic, but feel free to go well beyond \
what's literally written. Examples, analogies, related concepts, the bigger \
picture — that's the value you add.

How to handle different turns:

- Small talk ("hi", "yo", "thanks", "ok cool"): match their energy, keep it \
short, one casual sentence is plenty. Don't lecture, don't namecheck the \
section, don't say "I'm here to help" or "great to see you reading the \
notes". Just be a person.

- Topic questions: answer them fully and naturally. Pull from the notes when \
relevant, but enrich with your own knowledge — concrete examples, intuition, \
comparisons, why it matters. Do not give circular or tautological answers \
(e.g. "X is when something is X").

- Vague prompts ("explain this", "tell me more"): pick the most interesting \
idea from the section and actually teach it — 3-5 sentences with at least \
one concrete example.

- Clearly unrelated questions (recipes, sports, random trivia while studying \
something technical): briefly steer back to the topic. "Let's stay on \
[topic] — want me to walk through [related concept] instead?"

Examples of good replies (mimic this style and length):

Student: hi
You: Hey!

Student: hello
You: Hi — what do you want to dig into?

Student: yo
You: What's up?

Student: thanks
You: Anytime.

Student: ok cool
You: 👍

Student: what's the best pizza in town
You: Ha, can't help with food picks — but I can dig into anything from \
this section. Want me to walk through one of the ideas here?

Student: what's the weather like
You: Outside my lane! But if you're stuck on something in this section, \
I'm happy to unpack it.

Student: what is ai
You: AI is the idea of building machines that can do things we'd normally \
call "intelligent" — recognizing speech, spotting patterns, making \
decisions. Think of it as a giant umbrella; underneath it sits machine \
learning, where the machine figures out the rules from data instead of \
being hand-coded. A spam filter that gets smarter as it sees more emails \
is a small, real example.

Style:
- Vary your phrasing turn-to-turn. No template openings, no formulaic \
sentence structures.
- Friendly and direct. No filler ("Great question!", "I'd be happy to…", \
"Certainly!"). No stiff transitions ("In summary,", "To clarify,").
- NEVER write meta-commentary about the notes themselves. Don't say "the \
note doesn't go into that", "this section introduces X", "the notes \
mention…". Just answer.
- Plain prose. Use **bold** sparingly for genuinely key terms. Use bullet \
points (lines starting with "- ") only when listing 3+ distinct items.
- Keep replies under ~180 words.
"""


class ChatMessage(BaseModel):
    role: str
    content: str


class NotesChatRequest(BaseModel):
    topic: str
    section: str
    note_context: str
    history: list[ChatMessage] = []
    message: str


def _build_transcript(
    topic: str,
    section: str,
    note_context: str,
    history: list[ChatMessage],
    message: str,
) -> str:
    parts: list[str] = [
        f"Topic: {topic}",
        f"Section: {section}",
        "",
        "Note excerpt:",
        "---",
        note_context if note_context.strip() else "(no excerpt provided)",
        "---",
    ]
    if history:
        parts.append("")
        parts.append("Conversation so far:")
        for turn in history:
            speaker = "User" if turn.role == "user" else "Assistant"
            parts.append(f"{speaker}: {turn.content}")
    parts.append("")
    parts.append("New question from the student:")
    parts.append(message)
    return "\n".join(parts)


async def _stream_notes_chat(
    request: NotesChatRequest,
    user_id: Optional[str],
) -> AsyncIterator[str]:
    settings = get_settings()
    provider = resolve_provider_config(settings)

    if provider is None:
        yield "data: [LLM not configured — set GROQ_API_KEY or start the local LLM server]\n\n"
        return

    note_context = request.note_context[:800]
    message = request.message[:1500]

    conversation_id: str | None = None
    if user_id and request.topic:
        conversation_id = await get_or_create_conversation(
            user_id, "notes_chat", topic_id=request.topic
        )

    if conversation_id:
        db_messages = await fetch_recent_messages(conversation_id, limit=12)
        history: list[ChatMessage] = [ChatMessage(**m) for m in db_messages]
        await insert_message(conversation_id, "user", message)
    else:
        history = list(request.history[-6:])

    student_context = await build_student_context(user_id)
    system_prompt = NOTES_CHAT_SYSTEM_PROMPT + student_context

    transcript = _build_transcript(
        topic=request.topic,
        section=request.section,
        note_context=note_context,
        history=history,
        message=message,
    )

    assistant_chunks: list[str] = []
    async for token in stream_llm(
        transcript=transcript,
        system_prompt=system_prompt,
        provider_config=provider,
        temperature=0.4,
        max_tokens=400,
    ):
        assistant_chunks.append(token)
        safe = token.replace("\n", "\\n")
        yield f"data: {safe}\n\n"

    if conversation_id:
        full = "".join(assistant_chunks).strip()
        if full:
            await insert_message(conversation_id, "assistant", full)
        if user_id:
            import asyncio
            asyncio.create_task(
                maybe_refresh_summary(user_id, conversation_id=conversation_id)
            )

    yield "data: [DONE]\n\n"


@router.get("/chat/history")
async def notes_chat_history(
    topic: str,
    user_id: Optional[str] = Depends(require_user),
) -> dict:
    """Return persisted chat history for the current user + topic."""
    if not user_id or not topic:
        return {"messages": []}
    messages = await fetch_history_for_user(
        user_id, "notes_chat", topic_id=topic, limit=50
    )
    return {"messages": messages}


@router.post("/chat")
async def notes_chat(
    request: NotesChatRequest,
    user_id: Optional[str] = Depends(require_user),
) -> StreamingResponse:
    """
    Stream a topic-scoped tutor reply for the Study Notes page.

    The response is a Server-Sent Events stream. Each event contains a text
    chunk. The final event is `data: [DONE]`.
    """
    return StreamingResponse(
        _stream_notes_chat(request, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
