"""
Q&Ace — Punctuation-Triggered Buffer.

Accumulates streaming LLM tokens and fires sentence-level chunks
at punctuation boundaries. This enables low-latency TTS: each sentence
can be synthesised as soon as it's complete, without waiting for the
full LLM response.

Rules:
  - Fire immediately on sentence-ending punctuation: . ? !
  - Fire on clause-ending punctuation (, ; — :) when accumulated buffer ≥ 8 tokens.
  - Fire on flush (end of stream) regardless.
"""

from __future__ import annotations

import logging
import re
from typing import Callable, Optional

logger = logging.getLogger("qace.punctuation_buffer")

# Sentence endings → always fire
_SENTENCE_END = re.compile(r"[.!?]$")

# Clause endings → fire only if buffer has ≥ 8 tokens
_CLAUSE_END = re.compile(r"[,;:—–\-]$")

MIN_CLAUSE_TOKENS = 8


class PunctuationBuffer:
    """
    Accumulates streaming tokens and fires callbacks at punctuation boundaries.

    Usage:
        buf = PunctuationBuffer(on_chunk=handle_sentence)
        for token in llm_stream:
            buf.feed(token)
        buf.flush()
    """

    def __init__(
        self,
        on_chunk: Callable[[str], None],
        min_clause_tokens: int = MIN_CLAUSE_TOKENS,
    ):
        self._on_chunk = on_chunk
        self._min_clause_tokens = min_clause_tokens
        self._buffer: list[str] = []
        self._token_count: int = 0
        self._chunks_fired: int = 0

    def feed(self, token: str) -> None:
        """Feed a single token. May trigger on_chunk callback."""
        if not token:
            return

        self._buffer.append(token)
        self._token_count += 1

        # Check current accumulated text
        text = "".join(self._buffer).rstrip()

        if _SENTENCE_END.search(text):
            self._fire()
        elif _CLAUSE_END.search(text) and self._token_count >= self._min_clause_tokens:
            self._fire()

    def flush(self) -> None:
        """Fire any remaining buffered text."""
        if self._buffer:
            self._fire()

    def _fire(self) -> None:
        """Emit the current buffer as a chunk."""
        text = "".join(self._buffer).strip()
        if text:
            self._on_chunk(text)
            self._chunks_fired += 1
        self._buffer.clear()
        self._token_count = 0

    @property
    def chunks_fired(self) -> int:
        return self._chunks_fired

    def reset(self) -> None:
        """Clear state for a new utterance."""
        self._buffer.clear()
        self._token_count = 0
        self._chunks_fired = 0
