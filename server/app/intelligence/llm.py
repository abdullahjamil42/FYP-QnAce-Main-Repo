"""Q&Ace LLM client with Groq and Airforce provider support."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import threading
import urllib.request as urllib_request
import zipfile
from typing import Any, AsyncIterator

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("qace.llm")

LOCAL_LLM_SERVER_URL = "http://localhost:8081"

GROQ_PROVIDER = "groq"
AIRFORCE_PROVIDER = "airforce"
LOCAL_PROVIDER = "local"
AUTO_PROVIDER = "auto"


# For local LLM server, this is httpx.AsyncClient.
# For Groq, this is the Groq client.
LLMProvider = httpx.AsyncClient | Any


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider, resolved from settings."""

    model_config = {"arbitrary_types_allowed": True}

    provider: str
    client: LLMProvider
    model: str


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
    options: dict[str, Any] = field(default_factory=dict)


async def swap_adapter(adapter: str) -> bool:
    """Call the local LLM wrapper server to hot-swap the LoRA adapter."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{LOCAL_LLM_SERVER_URL}/swap-adapter/{adapter}")
            if resp.status_code == 200:
                logger.info("Swapped local LLM adapter to '%s'", adapter)
                return True
            else:
                logger.warning("Adapter swap to '%s' returned %d", adapter, resp.status_code)
                return False
    except Exception as exc:
        logger.warning("Could not swap adapter to '%s': %s", adapter, exc)
        return False


_LOCAL_MODEL = None
_LOCAL_TOKENIZER = None
_LOCAL_MODEL_ID = ""
_LOCAL_MODEL_LOCK = threading.Lock()


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
5. Keep your response concise (2-3 short sentences, max ~60 words).
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
    max_tokens: int = 120,
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
    max_tokens: int = 120,
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


def _resolve_local_model_path(model_ref: str) -> str:
    """Resolve local model path, optionally extracting a bundled zip package."""
    if not model_ref:
        return ""

    p = Path(model_ref)
    if not p.exists():
        return model_ref

    if p.is_file() and p.suffix.lower() == ".zip":
        extract_dir = p.with_suffix("")
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(p, "r") as zf:
            zf.extractall(extract_dir)
        return str(extract_dir)

    if p.is_dir():
        # If a model folder only contains a zip package, extract it automatically.
        zip_files = sorted([f for f in p.iterdir() if f.is_file() and f.suffix.lower() == ".zip"])
        if len(zip_files) == 1 and not (p / "config.json").exists():
            extract_dir = p / zip_files[0].stem
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_files[0], "r") as zf:
                zf.extractall(extract_dir)
            return str(extract_dir)

    return str(p)


def _get_torch_dtype(dtype_name: str):
    import torch

    dn = (dtype_name or "auto").strip().lower()
    if dn in {"fp16", "float16", "half"}:
        return torch.float16
    if dn in {"bf16", "bfloat16"}:
        return torch.bfloat16
    if dn in {"fp32", "float32"}:
        return torch.float32
    if torch.cuda.is_available():
        return torch.float16
    return torch.float32


def _load_local_model(model_path: str, device: str, dtype_name: str, adapter_path: str = ""):
    global _LOCAL_MODEL, _LOCAL_TOKENIZER, _LOCAL_MODEL_ID

    resolved_path = _resolve_local_model_path(model_path)
    resolved_adapter_path = _resolve_local_model_path(adapter_path) if adapter_path else ""
    model_id = f"{resolved_path}|{resolved_adapter_path}|{device}|{dtype_name}"
    if _LOCAL_MODEL is not None and _LOCAL_TOKENIZER is not None and _LOCAL_MODEL_ID == model_id:
        return _LOCAL_MODEL, _LOCAL_TOKENIZER

    with _LOCAL_MODEL_LOCK:
        if _LOCAL_MODEL is not None and _LOCAL_TOKENIZER is not None and _LOCAL_MODEL_ID == model_id:
            return _LOCAL_MODEL, _LOCAL_TOKENIZER

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("transformers/torch not installed for local LLM") from exc

        if not resolved_path:
            raise RuntimeError("Local LLM path is not configured")

        logger.info("Loading local LLM from %s", resolved_path)
        torch_dtype = _get_torch_dtype(dtype_name)
        use_cuda = (device in {"auto", "cuda"}) and torch.cuda.is_available()
        model_local_only = Path(resolved_path).exists()
        is_peft_mode = bool(resolved_adapter_path)

        if is_peft_mode:
            try:
                from peft import PeftModel
            except ImportError as exc:
                raise RuntimeError("peft not installed for local adapter inference") from exc

            logger.info("Attaching local LoRA adapter from %s", resolved_adapter_path)
            tokenizer = AutoTokenizer.from_pretrained(resolved_path, local_files_only=model_local_only)
            model = AutoModelForCausalLM.from_pretrained(
                resolved_path,
                local_files_only=model_local_only,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
            )
            model = PeftModel.from_pretrained(model, resolved_adapter_path, is_trainable=False)
        else:
            tokenizer = AutoTokenizer.from_pretrained(resolved_path, local_files_only=model_local_only)
            model = AutoModelForCausalLM.from_pretrained(
                resolved_path,
                local_files_only=model_local_only,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
            )

        if getattr(tokenizer, "pad_token_id", None) is None and getattr(tokenizer, "eos_token_id", None) is not None:
            tokenizer.pad_token_id = tokenizer.eos_token_id

        if use_cuda:
            model = model.to("cuda")
        else:
            model = model.to("cpu")

        model.eval()
        _LOCAL_MODEL = model
        _LOCAL_TOKENIZER = tokenizer
        _LOCAL_MODEL_ID = model_id
        logger.info("Local LLM loaded ✓ (%s)", resolved_path)
        return _LOCAL_MODEL, _LOCAL_TOKENIZER


def _build_local_prompt(system_prompt: str, transcript: str, tokenizer: Any) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcript},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return f"System: {system_prompt}\n\nUser: {transcript}\n\nAssistant:"


def _generate_local_text(
    transcript: str,
    system_prompt: str,
    model_path: str,
    temperature: float,
    max_tokens: int,
    options: dict[str, Any],
) -> str:
    import torch

    device = str(options.get("device", "auto"))
    dtype_name = str(options.get("dtype", "auto"))
    base_model = str(options.get("base_model", "") or "").strip()
    adapter_path = str(options.get("adapter_path", "") or "").strip()
    effective_model_path = base_model or model_path
    model, tokenizer = _load_local_model(effective_model_path, device, dtype_name, adapter_path)

    prompt = _build_local_prompt(system_prompt, transcript, tokenizer)
    inputs = tokenizer(prompt, return_tensors="pt")
    model_device = next(model.parameters()).device
    inputs = {k: v.to(model_device) for k, v in inputs.items()}

    do_sample = float(temperature) > 0.0
    gen_kwargs = {
        "max_new_tokens": int(max_tokens),
        "do_sample": do_sample,
        "temperature": max(float(temperature), 1e-5) if do_sample else 1.0,
        "pad_token_id": tokenizer.eos_token_id,
    }

    with torch.inference_mode():
        output = model.generate(**inputs, **gen_kwargs)

    prompt_len = int(inputs["input_ids"].shape[1])
    generated_ids = output[0][prompt_len:]
    text = tokenizer.decode(generated_ids, skip_special_tokens=True)
    return str(text).strip()


async def stream_local(
    transcript: str,
    system_prompt: str,
    model_path: str,
    temperature: float = 0.7,
    max_tokens: int = 120,
    options: Optional[dict[str, Any]] = None,
) -> AsyncIterator[str]:
    """Run local model generation and yield text in small chunks."""
    opts = dict(options or {})
    t0 = time.perf_counter()
    try:
        loop = __import__("asyncio").get_running_loop()
        text = await loop.run_in_executor(
            None,
            _generate_local_text,
            transcript,
            system_prompt,
            model_path,
            temperature,
            max_tokens,
            opts,
        )
    except Exception as exc:
        logger.error("Local LLM generation error: %s", exc)
        yield f"[Local LLM error: {exc}]"
        return

    if not text:
        yield "[Local LLM produced empty response]"
        return

    ttft = (time.perf_counter() - t0) * 1000.0
    logger.info("Local LLM TTFT: %.0fms", ttft)

    words = text.split()
    chunk_size = 12
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i:i + chunk_size]) + (" " if i + chunk_size < len(words) else "")


async def stream_local_endpoint(
    transcript: str,
    system_prompt: str,
    base_url: str,
    api_key: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 120,
) -> AsyncIterator[str]:
    """Stream from an OpenAI-compatible local endpoint (/v1/chat/completions)."""
    try:
        import httpx
    except ImportError:
        logger.error("httpx not installed — local endpoint streaming unavailable")
        yield "[httpx not installed]"
        return

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    t0 = time.perf_counter()
    first_token = True
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    logger.error("Local endpoint error %d: %s", response.status_code, body[:200])
                    yield f"[Local endpoint error {response.status_code}]"
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
                                logger.info("Local endpoint TTFT: %.0fms", ttft)
                                first_token = False
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                        continue
    except Exception as exc:
        logger.error("Local endpoint streaming error: %s", exc)
        yield f"[Local endpoint error: {exc}]"


def check_local_llm_endpoint(base_url: str, timeout_s: float = 2.0) -> tuple[bool, str]:
    """Quick startup probe for OpenAI-compatible local endpoint health."""
    url = (base_url or "").strip()
    if not url:
        return False, "QACE_LOCAL_LLM_BASE_URL is empty"

    health_url = f"{url.rstrip('/')}/health"
    try:
        req = urllib_request.Request(health_url, method="GET")
        with urllib_request.urlopen(req, timeout=timeout_s) as resp:  # nosec B310 - local user-configured URL
            status = int(getattr(resp, "status", 0) or 0)
            if 200 <= status < 300:
                return True, f"reachable ({health_url})"
            return False, f"unexpected status {status} ({health_url})"
    except Exception as exc:
        return False, f"unreachable ({health_url}): {exc}"


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

    if preferred == LOCAL_PROVIDER:
        local_model = generic_model or getattr(settings, "local_llm_path", "")
        local_base_model = getattr(settings, "local_llm_base_model", "")
        local_adapter_path = getattr(settings, "local_llm_adapter_path", "")
        if not local_model and not local_base_model:
            return None
        return LLMProviderConfig(
            LOCAL_PROVIDER,
            "",
            local_base_model or local_model,
            options={
                "local_model_path": local_model,
                "base_model": local_base_model,
                "adapter_path": local_adapter_path,
                "base_url": getattr(settings, "local_llm_base_url", ""),
                "api_key": getattr(settings, "local_llm_api_key", ""),
                "device": getattr(settings, "local_llm_device", "auto"),
                "dtype": getattr(settings, "local_llm_dtype", "auto"),
            },
        )

    groq_api_key = getattr(settings, "groq_api_key", "")
    if groq_api_key:
        return LLMProviderConfig(GROQ_PROVIDER, groq_api_key, generic_model or getattr(settings, "groq_model", "llama-3.3-70b-versatile"))

    airforce_api_key = getattr(settings, "airforce_api_key", "")
    if airforce_api_key:
        return LLMProviderConfig(AIRFORCE_PROVIDER, airforce_api_key, generic_model or getattr(settings, "airforce_model", "deepseek-v3"))

    local_model = generic_model or getattr(settings, "local_llm_path", "")
    local_base_model = getattr(settings, "local_llm_base_model", "")
    local_adapter_path = getattr(settings, "local_llm_adapter_path", "")
    if local_model or local_base_model:
        return LLMProviderConfig(
            LOCAL_PROVIDER,
            "",
            local_base_model or local_model,
            options={
                "local_model_path": local_model,
                "base_model": local_base_model,
                "adapter_path": local_adapter_path,
                "base_url": getattr(settings, "local_llm_base_url", ""),
                "api_key": getattr(settings, "local_llm_api_key", ""),
                "device": getattr(settings, "local_llm_device", "auto"),
                "dtype": getattr(settings, "local_llm_dtype", "auto"),
            },
        )

    return None


async def stream_llm(
    transcript: str,
    system_prompt: str,
    provider_config: LLMProviderConfig,
    temperature: float = 0.7,
    max_tokens: int = 120,
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

    if provider_config.provider == LOCAL_PROVIDER:
        base_url = str(provider_config.options.get("base_url", "") or "").strip()
        api_key = str(provider_config.options.get("api_key", "") or "").strip()
        if base_url:
            async for token in stream_local_endpoint(
                transcript,
                system_prompt,
                base_url,
                api_key,
                provider_config.model,
                temperature,
                max_tokens,
            ):
                yield token
        else:
            async for token in stream_local(
                transcript,
                system_prompt,
                provider_config.model,
                temperature,
                max_tokens,
                provider_config.options,
            ):
                yield token
        return

    logger.error("Unsupported LLM provider: %s", provider_config.provider)
    yield f"[Unsupported LLM provider: {provider_config.provider}]"


async def generate_feedback(
    transcript: str,
    system_prompt: str,
    provider_config: LLMProviderConfig,
    temperature: float = 0.7,
    max_tokens: int = 120,
) -> LLMStreamResult:
    """
    Non-streaming convenience: collects all tokens and returns full text + timing.
    Use when you don't need punctuation-buffer streaming.
    """
    tokens: list[str] = []
    t0 = time.perf_counter()
    ttft = 0.0

    async for token in stream_llm(
        transcript, system_prompt, provider_config, temperature, max_tokens
    ):
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


async def call_llm(
    messages: list[dict],
    provider_config: LLMProviderConfig,
    temperature: float = 0.3,
    max_tokens: int = 256,
    timeout_s: float = 3.0,
) -> str | None:
    """
    Non-streaming LLM call with timeout.

    Reuses the same provider routing as ``stream_llm`` but makes a single
    request and returns the full text.  Wrapped in ``asyncio.wait_for``
    so a slow API response never blocks the interview pipeline.

    Returns ``None`` on timeout or any exception — callers supply their
    own fallback values.
    """
    import asyncio

    system_msg = ""
    user_msg = ""
    for m in messages:
        if m.get("role") == "system":
            system_msg = m.get("content", "")
        elif m.get("role") == "user":
            user_msg = m.get("content", "")

    async def _run() -> str:
        result = await generate_feedback(
            transcript=user_msg,
            system_prompt=system_msg,
            provider_config=provider_config,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return result.full_text

    try:
        text = await asyncio.wait_for(_run(), timeout=timeout_s)
        return text if text else None
    except asyncio.TimeoutError:
        logger.warning("call_llm timed out after %.1fs", timeout_s)
        return None
    except Exception as exc:
        logger.warning("call_llm failed: %s", exc)
        return None
