"""Strip markdown code fences from LLM output before JSON parsing."""

from __future__ import annotations

import re

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE | re.IGNORECASE)


def strip_markdown_fences(text: str) -> str:
    t = text.strip()
    t = _FENCE.sub("", t).strip()
    return t
