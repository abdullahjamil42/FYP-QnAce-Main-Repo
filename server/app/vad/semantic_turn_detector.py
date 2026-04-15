"""
Q&Ace — Semantic turn detector.

This module provides a low-latency state machine that decides when the user has
finished their speaking turn by combining silence duration with transcript
completeness.

Design goals:
- No external APIs (local-only inference).
- Preload model once to avoid cold starts in hot path.
- Fast repeated calls via caching and short sequence truncation.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Optional

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger("qace.semantic_turn")


class SemanticTurnDetector:
    """State-machine based semantic turn detector.

    Gates:
    1) Micro-pause gate: silence < min_silence_ms -> False.
    2) Semantic gate: min_silence_ms <= silence < max_silence_ms ->
       evaluate transcript completeness and compare with semantic_threshold.
    3) Hard cutoff gate: silence >= max_silence_ms -> True.
    """

    def __init__(
        self,
        min_silence_ms: int = 400,
        max_silence_ms: int = 1500,
        semantic_threshold: float = 0.85,
        model_name: Optional[str] = "distilbert-base-uncased-finetuned-sst-2-english",
        max_length: int = 64,
        cache_size: int = 128,
    ) -> None:
        if min_silence_ms < 0:
            raise ValueError("min_silence_ms must be >= 0")
        if max_silence_ms <= min_silence_ms:
            raise ValueError("max_silence_ms must be greater than min_silence_ms")
        if not (0.0 <= semantic_threshold <= 1.0):
            raise ValueError("semantic_threshold must be between 0.0 and 1.0")
        if max_length < 8:
            raise ValueError("max_length must be >= 8")
        if cache_size < 1:
            raise ValueError("cache_size must be >= 1")

        self.min_silence_ms = int(min_silence_ms)
        self.max_silence_ms = int(max_silence_ms)
        self.semantic_threshold = float(semantic_threshold)
        self.max_length = int(max_length)
        self.cache_size = int(cache_size)

        self._tokenizer = None
        self._model = None
        self._use_model = False
        self._cache: OrderedDict[str, float] = OrderedDict()

        if model_name:
            try:
                self._tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=False)
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    model_name,
                    local_files_only=False,
                )
                self._model.eval()
                self._use_model = True
                logger.info("Semantic model loaded: %s", model_name)
            except Exception as exc:
                # Keep detector functional with heuristic-only mode.
                logger.warning("Semantic model load failed (%s); using heuristic-only mode", exc)
                self._use_model = False

    def evaluate_turn(self, current_silence_duration_ms: int, partial_transcript: str) -> bool:
        """Return True when turn should end and AI can respond."""
        # Gate 1: micro-pause (breathing / mid-thought pause)
        if current_silence_duration_ms < self.min_silence_ms:
            return False

        # Gate 3: hard cutoff
        if current_silence_duration_ms >= self.max_silence_ms:
            return True

        # Gate 2: semantic check in the middle band.
        completeness_probability = self.score_completeness(partial_transcript)
        return completeness_probability > self.semantic_threshold

    def score_completeness(self, partial_transcript: str) -> float:
        """Return a completeness probability in [0.0, 1.0]."""
        text = (partial_transcript or "").strip()
        if not text:
            return 0.0

        cached = self._cache_get(text)
        if cached is not None:
            return cached

        boundary_score = self._boundary_score(text)
        if not self._use_model:
            self._cache_put(text, boundary_score)
            return boundary_score

        semantic_score = self._model_score(text)

        # Blend model signal with punctuation/grammar boundary signal.
        # Boundary is weighted higher because this class is sentence-completion focused.
        probability = 0.65 * boundary_score + 0.35 * semantic_score
        probability = min(1.0, max(0.0, probability))
        self._cache_put(text, probability)
        return probability

    @torch.inference_mode()
    def _model_score(self, text: str) -> float:
        # Small max_length keeps latency low for continuous polling loops.
        encoded = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
            padding=False,
        )
        outputs = self._model(**encoded)
        probs = torch.softmax(outputs.logits, dim=-1).squeeze(0)

        # For binary sequence-classification heads we use max class confidence
        # as a compact proxy for semantic confidence.
        return float(torch.max(probs).item())

    def _boundary_score(self, text: str) -> float:
        lowered = text.strip().lower()
        words = lowered.split()
        n_words = len(words)
        ends_terminal = lowered.endswith((".", "?", "!"))

        dangling_tail = {
            "and",
            "or",
            "but",
            "because",
            "so",
            "then",
            "that",
            "which",
            "who",
            "when",
            "where",
            "while",
            "by",
            "to",
            "with",
            "for",
            "if",
        }
        tail = words[-1] if words else ""

        # Clear sentence boundary.
        if ends_terminal and n_words >= 4:
            return 0.96

        # Strongly incomplete phrase cues.
        if tail in dangling_tail:
            return 0.18

        # Very short utterances are usually not complete interview answers.
        if n_words <= 2:
            return 0.22

        # Mid-confidence baseline for natural pauses in partial answers.
        if lowered.endswith((",", ":", ";")):
            return 0.35

        # If it has reasonable length without terminal punctuation,
        # treat as uncertain but potentially complete.
        return 0.62 if n_words >= 8 else 0.48

    def _cache_get(self, key: str) -> Optional[float]:
        value = self._cache.get(key)
        if value is not None:
            self._cache.move_to_end(key)
        return value

    def _cache_put(self, key: str, value: float) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)
