"""
Q&Ace — Preparation Module Endpoints
Generates and manages study notes for technical interview topics.
"""

import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .config import get_settings
from .intelligence.llm import (
    LLMProvider,
    ProviderConfig,
    resolve_provider_config,
    stream_llm,
)

logger = logging.getLogger("qace.preparation")

router = APIRouter()

def get_llm_provider() -> ProviderConfig | None:
    """FastAPI dependency to resolve LLM provider config."""
    settings = get_settings()
    return resolve_provider_config(settings)

class GenerateNotesRequest(BaseModel):
    topic: str

class NotesResponse(BaseModel):
    topic: str
    notes_markdown: str

@router.post(
    "/generate-notes",
    response_model=NotesResponse,
    summary="Generate study notes for a topic",
    description="Uses the configured LLM to generate detailed, structured study notes in Markdown format for a given technical topic.",
)
async def generate_notes(
    request: GenerateNotesRequest,
    llm_provider: LLMProvider = Depends(get_llm_provider),
):
    """
    Generates extensive, structured study notes for a given topic using an LLM.
    """
    topic = request.topic
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    logger.info(f"Generating study notes for topic: {topic}")

    system_prompt = """
You are an expert AI assistant tasked with creating high-quality, structured study notes for a senior software engineer preparing for a technical interview.
The notes must be in Markdown format.
For the given topic, you must:
1.  Create a main heading for the topic.
2.  Break the topic down into logical sub-topics, each with a level-2 heading (##).
3.  For each sub-topic, provide detailed explanations, key concepts, and important principles using level-3 headings (###).
4.  Include bullet points, code snippets (if applicable), and clear examples to illustrate complex ideas.
5.  Conclude with a "Key Takeaways" or "Common Pitfalls" section.
Do not include any conversational text or introductory/concluding sentences outside of the notes themselves. The output should be pure Markdown.
"""
    user_prompt = f"Topic: {topic}"

    try:
        response_chunks = []
        async for chunk in stream_llm(
            transcript=user_prompt,
            system_prompt=system_prompt,
            provider_config=llm_provider,
            max_tokens=2048, # Allow for longer, more detailed notes
            temperature=0.3, # Keep it factual and structured
        ):
            response_chunks.append(chunk)
        
        full_response = "".join(response_chunks)

        return NotesResponse(topic=topic, notes_markdown=full_response)

    except Exception as e:
        logger.error(f"Error generating notes for topic '{topic}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate notes. Error: {e}")
