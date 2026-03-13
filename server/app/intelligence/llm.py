"""Q&Ace LLM client with Groq and Airforce provider support."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
import json
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger("qace.llm")

GROQ_PROVIDER = "groq"
AIRFORCE_PROVIDER = "airforce"
AUTO_PROVIDER = "auto"


@dataclass
class LLMStreamResult:
    """Metadata collected after a complete LLM stream."""
    full_text: str = ""
    ttft_ms: float = 0.0       # time to first token
    total_ms: float = 0.0      # wall-clock start to last token
    token_count: int = 0
    model: str = ""


@dataclass
class LLMProviderConfig:
    provider: str
    api_key: str
    model: str


# ── System Prompt ──

SYSTEM_PROMPT = """\
You are Q&Ace, an AI mock-interview coach. Your role is to provide constructive,
specific, and encouraging feedback to help candidates improve their interview
performance.

## Your Personality
- Professional but warm — like a supportive senior colleague.
- Direct and specific — avoid filler phrases like "Great question!" or "That's interesting."
- Always provide actionable next steps.

## Rubric Context (retrieved from knowledge base)
{rubric_context}

## Current Perception Data
- Vocal emotion: {vocal_emotion} (confidence: {acoustic_confidence:.0%})
- Face emotion: {face_emotion}
- Text quality: {text_quality_label} (score: {text_quality_score:.0f}/100)
- Speaking rate: {wpm:.0f} WPM | Fillers: {filler_count}

## Instructions
1. Evaluate the candidate's response against the provided rubric context.
2. Identify 1-2 specific strengths and 1-2 areas for improvement.
3. If the response follows STAR method well, acknowledge it specifically.
4. If the response lacks structure, suggest how to restructure using STAR.
5. Keep your response concise (3-5 sentences).
6. End with one specific, actionable tip for their next answer.
7. If their delivery data suggests nervousness, address it gently.
"""


def build_system_prompt(
    rubric_context: str = "",
    vocal_emotion: str = "neutral",
    acoustic_confidence: float = 0.0,
    face_emotion: str = "neutral",
    text_quality_label: str = "average",
    text_quality_score: float = 60.0,
    wpm: float = 0.0,
    filler_count: int = 0,
) -> str:
    """Build the system prompt with injected rubric context and perception data."""
    return SYSTEM_PROMPT.format(
        rubric_context=rubric_context or "(No rubric context available)",
        vocal_emotion=vocal_emotion,
        acoustic_confidence=acoustic_confidence,
        face_emotion=face_emotion,
        text_quality_label=text_quality_label,
        text_quality_score=text_quality_score,
        wpm=wpm,
        filler_count=filler_count,
    )


async def stream_groq(
    transcript: str,
    system_prompt: str,
    api_key: str,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> AsyncIterator[str]:
    """
    Stream tokens from Groq's chat completion API via httpx SSE.

    Yields individual token strings as they arrive.
    """
    if not api_key:
        logger.warning("GROQ_API_KEY not set — LLM response unavailable")
        yield "[LLM unavailable — set GROQ_API_KEY]"
        return

    try:
        import httpx
    except ImportError:
        logger.error("httpx not installed — LLM streaming unavailable")
        yield "[httpx not installed]"
        return

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Candidate's response:\n\n{transcript}"},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    t0 = time.perf_counter()
    first_token = True

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            async with client.stream(
                "POST", url, headers=headers, json=payload
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    logger.error("Groq API error %d: %s", response.status_code, body[:200])
                    yield f"[Groq error {response.status_code}]"
                    return

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            if first_token:
                                ttft = (time.perf_counter() - t0) * 1000.0
                                logger.info("Groq TTFT: %.0fms", ttft)
                                first_token = False
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    except httpx.TimeoutException:
        logger.error("Groq request timed out")
        yield "[LLM timeout]"
    except Exception as exc:
        logger.error("Groq streaming error: %s", exc)
        yield f"[LLM error: {exc}]"


def extract_chat_content(payload: dict[str, Any]) -> str:
    """Extract assistant content from an OpenAI-compatible chat response."""
    try:
        message = payload["choices"][0]["message"]
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "".join(parts)
    except (KeyError, IndexError, TypeError):
        return ""
    return ""


async def stream_airforce(
    transcript: str,
    system_prompt: str,
    api_key: str,
    model: str = "deepseek-v3",
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> AsyncIterator[str]:
    """Call Airforce chat completions and yield the full response as one chunk."""
    if not api_key:
        logger.warning("AIRFORCE_API_KEY not set — LLM response unavailable")
        yield "[LLM unavailable — set AIRFORCE_API_KEY]"
        return

    try:
        import httpx
    except ImportError:
        logger.error("httpx not installed — LLM streaming unavailable")
        yield "[httpx not installed]"
        return

    url = "https://api.airforce/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Candidate's response:\n\n{transcript}"},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    t0 = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error("Airforce API error %d: %s", response.status_code, response.text[:200])
                yield f"[Airforce error {response.status_code}]"
                return

            content = extract_chat_content(response.json())
            if content:
                ttft = (time.perf_counter() - t0) * 1000.0
                logger.info("Airforce TTFR: %.0fms", ttft)
                yield content
                return

            logger.error("Airforce response missing assistant content")
            yield "[Airforce response malformed]"
    except httpx.TimeoutException:
        logger.error("Airforce request timed out")
        yield "[LLM timeout]"
    except Exception as exc:
        logger.error("Airforce request error: %s", exc)
        yield f"[LLM error: {exc}]"


def resolve_provider_config(settings: Any) -> Optional[LLMProviderConfig]:
    """Resolve the active provider from settings, honoring explicit override first."""
    preferred = getattr(settings, "normalized_llm_provider", AUTO_PROVIDER)
    generic_model = getattr(settings, "llm_model", "")

    if preferred == GROQ_PROVIDER:
        api_key = getattr(settings, "groq_api_key", "")
        if not api_key:
            return None
        return LLMProviderConfig(GROQ_PROVIDER, api_key, generic_model or getattr(settings, "groq_model", "llama-3.3-70b-versatile"))

    if preferred == AIRFORCE_PROVIDER:
        api_key = getattr(settings, "airforce_api_key", "")
        if not api_key:
            return None
        return LLMProviderConfig(AIRFORCE_PROVIDER, api_key, generic_model or getattr(settings, "airforce_model", "deepseek-v3"))

    groq_api_key = getattr(settings, "groq_api_key", "")
    if groq_api_key:
        return LLMProviderConfig(GROQ_PROVIDER, groq_api_key, generic_model or getattr(settings, "groq_model", "llama-3.3-70b-versatile"))

    airforce_api_key = getattr(settings, "airforce_api_key", "")
    if airforce_api_key:
        return LLMProviderConfig(AIRFORCE_PROVIDER, airforce_api_key, generic_model or getattr(settings, "airforce_model", "deepseek-v3"))

    return None


async def stream_llm(
    transcript: str,
    system_prompt: str,
    provider_config: LLMProviderConfig,
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> AsyncIterator[str]:
    """Provider-neutral LLM stream wrapper."""
    if provider_config.provider == GROQ_PROVIDER:
        async for token in stream_groq(
            transcript,
            system_prompt,
            provider_config.api_key,
            provider_config.model,
            temperature,
            max_tokens,
        ):
            yield token
        return

    if provider_config.provider == AIRFORCE_PROVIDER:
        async for token in stream_airforce(
            transcript,
            system_prompt,
            provider_config.api_key,
            provider_config.model,
            temperature,
            max_tokens,
        ):
            yield token
        return

    logger.error("Unsupported LLM provider: %s", provider_config.provider)
    yield f"[Unsupported LLM provider: {provider_config.provider}]"


async def generate_feedback(
    transcript: str,
    system_prompt: str,
    provider_config: LLMProviderConfig,
) -> LLMStreamResult:
    """
    Non-streaming convenience: collects all tokens and returns full text + timing.
    Use when you don't need punctuation-buffer streaming.
    """
    tokens: list[str] = []
    t0 = time.perf_counter()
    ttft = 0.0

    async for token in stream_llm(transcript, system_prompt, provider_config):
        if not tokens:
            ttft = (time.perf_counter() - t0) * 1000.0
        tokens.append(token)

    full_text = "".join(tokens)
    total_ms = (time.perf_counter() - t0) * 1000.0

    return LLMStreamResult(
        full_text=full_text,
        ttft_ms=round(ttft, 1),
        total_ms=round(total_ms, 1),
        token_count=len(tokens),
        model=provider_config.model,
    )
