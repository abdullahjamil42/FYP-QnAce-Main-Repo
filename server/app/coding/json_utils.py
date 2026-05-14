"""LLM JSON extraction utilities for the coding module."""

from __future__ import annotations

import json
import re

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE | re.IGNORECASE)


def extract_json(text: str) -> dict | None:
    """
    Robustly extract the first JSON object from an LLM response.

    Strategy:
    1. Find the first '{' and last '}' in the text.
    2. Attempt json.loads on that substring.
    3. Return None if not found or parse fails.
    """
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def strip_markdown_fences(text: str) -> str:
    """Legacy shim — strips markdown fences and returns cleaned text."""
    t = text.strip()
    t = _FENCE.sub("", t).strip()
    return t
