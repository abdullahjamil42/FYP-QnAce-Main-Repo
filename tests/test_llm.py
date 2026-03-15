from __future__ import annotations

from types import SimpleNamespace

from server.app.intelligence.llm import (
    AIRFORCE_PROVIDER,
    GROQ_PROVIDER,
    LOCAL_PROVIDER,
    extract_chat_content,
    resolve_provider_config,
)


def make_settings(**overrides):
    defaults = {
        "normalized_llm_provider": "auto",
        "llm_model": "",
        "groq_api_key": "",
        "groq_model": "llama-3.3-70b-versatile",
        "airforce_api_key": "",
        "airforce_model": "deepseek-v3",
        "local_llm_path": "",
        "local_llm_base_model": "",
        "local_llm_adapter_path": "",
        "local_llm_base_url": "",
        "local_llm_api_key": "",
        "local_llm_device": "auto",
        "local_llm_dtype": "auto",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_resolve_provider_prefers_explicit_airforce():
    settings = make_settings(
        normalized_llm_provider="airforce",
        airforce_api_key="af-key",
        groq_api_key="groq-key",
    )
    provider = resolve_provider_config(settings)
    assert provider is not None
    assert provider.provider == AIRFORCE_PROVIDER
    assert provider.api_key == "af-key"
    assert provider.model == "deepseek-v3"


def test_resolve_provider_defaults_to_groq_when_auto():
    settings = make_settings(
        normalized_llm_provider="auto",
        groq_api_key="groq-key",
        airforce_api_key="af-key",
    )
    provider = resolve_provider_config(settings)
    assert provider is not None
    assert provider.provider == GROQ_PROVIDER
    assert provider.api_key == "groq-key"


def test_resolve_provider_uses_generic_model_override():
    settings = make_settings(
        normalized_llm_provider="airforce",
        airforce_api_key="af-key",
        llm_model="deepseek-r1",
    )
    provider = resolve_provider_config(settings)
    assert provider is not None
    assert provider.model == "deepseek-r1"


def test_resolve_provider_local_when_explicit():
    settings = make_settings(
        normalized_llm_provider="local",
        local_llm_path="C:/models/local-llm",
        local_llm_base_model="meta-llama/Meta-Llama-3.1-8B-Instruct",
        local_llm_adapter_path="C:/models/adapters/evaluator",
        local_llm_base_url="http://127.0.0.1:8081",
        local_llm_api_key="local-key",
        local_llm_device="cuda",
        local_llm_dtype="float16",
    )
    provider = resolve_provider_config(settings)
    assert provider is not None
    assert provider.provider == LOCAL_PROVIDER
    assert provider.model == "meta-llama/Meta-Llama-3.1-8B-Instruct"
    assert provider.options["local_model_path"] == "C:/models/local-llm"
    assert provider.options["base_model"] == "meta-llama/Meta-Llama-3.1-8B-Instruct"
    assert provider.options["adapter_path"] == "C:/models/adapters/evaluator"
    assert provider.options["base_url"] == "http://127.0.0.1:8081"
    assert provider.options["api_key"] == "local-key"
    assert provider.options["device"] == "cuda"
    assert provider.options["dtype"] == "float16"


def test_extract_chat_content_from_string_message():
    payload = {
        "choices": [
            {"message": {"role": "assistant", "content": "Use STAR more explicitly."}}
        ]
    }
    assert extract_chat_content(payload) == "Use STAR more explicitly."


def test_extract_chat_content_from_content_parts():
    payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Lead with context. "},
                        {"type": "text", "text": "Quantify the outcome."},
                    ],
                }
            }
        ]
    }
    assert extract_chat_content(payload) == "Lead with context. Quantify the outcome."