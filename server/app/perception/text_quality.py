"""
Q&Ace — Custom BERT ONNX Text Quality Scorer.

Classifies interview response quality into Poor / Average / Excellent
with interpolated probabilities.

Architecture:
  - Custom fine-tuned BERT model exported to ONNX.
  - Runs on GPU (but after Whisper finishes, sequential on critical path).
  - Input: transcript text (string).
  - Output: TextQualityResult with classification and probabilities.
  - Target: ~4ms on GPU for 50-100 tokens.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("qace.text_quality")

# Quality labels from our custom fine-tuned BERT
QUALITY_LABELS = ["poor", "average", "excellent"]

# Base scores for each quality level (interpolated via probabilities)
QUALITY_BASE_SCORES = {
    "poor": 30.0,
    "average": 60.0,
    "excellent": 90.0,
}


@dataclass
class TextQualityResult:
    """Result from BERT text quality classification."""
    label: str = "average"   # poor | average | excellent
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    base_score: float = 60.0  # interpolated score 0-100
    inference_ms: float = 0.0


def _simple_tokenize(text: str, max_length: int = 128) -> tuple[np.ndarray, np.ndarray]:
    """
    Simple whitespace tokenizer that produces BERT-compatible input_ids
    and attention_mask. This is a placeholder — real deployment will use
    the actual tokenizer from the fine-tuned model.

    Produces: [CLS] word_ids... [SEP] [PAD]...
    """
    # Simple word-level token mapping (ASCII hash to vocab range)
    words = text.lower().split()[:max_length - 2]
    
    # [CLS]=101, [SEP]=102, [PAD]=0
    input_ids = [101]  # CLS
    for word in words:
        # Hash word to a token in BERT vocab range (1000-30000)
        token_id = (hash(word) % 29000) + 1000
        input_ids.append(token_id)
    input_ids.append(102)  # SEP
    
    attention_mask = [1] * len(input_ids)
    
    # Pad to max_length
    while len(input_ids) < max_length:
        input_ids.append(0)
        attention_mask.append(0)
    
    return (
        np.array([input_ids], dtype=np.int64),
        np.array([attention_mask], dtype=np.int64),
    )


def _heuristic_quality(text: str) -> TextQualityResult:
    """
    Rule-based fallback when BERT model is unavailable.
    Uses text length, structure, and keyword presence as proxies.
    """
    words = text.split()
    word_count = len(words)
    
    # Basic quality signals
    has_structure = any(kw in text.lower() for kw in [
        "first", "then", "because", "therefore", "for example",
        "in my experience", "specifically", "as a result",
        "situation", "task", "action", "result",  # STAR method
    ])
    has_detail = word_count > 30
    has_specifics = any(char.isdigit() for char in text)  # contains numbers
    sentence_count = text.count(".") + text.count("!") + text.count("?")
    
    # Score components
    length_score = min(word_count / 50.0, 1.0)  # up to 50 words = full credit
    structure_score = 0.3 if has_structure else 0.0
    detail_score = 0.2 if has_detail else 0.0
    specifics_score = 0.1 if has_specifics else 0.0
    sentence_score = min(sentence_count / 3.0, 0.2)  # up to 3 sentences
    
    raw_score = length_score * 0.4 + structure_score + detail_score + specifics_score + sentence_score
    raw_score = max(0.0, min(1.0, raw_score))
    
    # Map to quality categories
    if raw_score >= 0.65:
        probs = {"poor": 0.05, "average": 0.25, "excellent": 0.70}
        label = "excellent"
    elif raw_score >= 0.35:
        probs = {"poor": 0.15, "average": 0.65, "excellent": 0.20}
        label = "average"
    else:
        probs = {"poor": 0.65, "average": 0.30, "excellent": 0.05}
        label = "poor"
    
    base_score = sum(
        QUALITY_BASE_SCORES[k] * v for k, v in probs.items()
    )
    
    return TextQualityResult(
        label=label,
        probabilities=probs,
        confidence=probs[label],
        base_score=round(base_score, 1),
    )


def classify_quality(text: str, bert_model: Any, tokenizer: Any = None) -> TextQualityResult:
    """
    Classify interview response quality using BERT ONNX model.

    Falls back to heuristic scoring when model is unavailable.
    """
    if not text or not text.strip():
        return TextQualityResult(
            label="poor",
            probabilities={"poor": 1.0, "average": 0.0, "excellent": 0.0},
            confidence=1.0,
            base_score=30.0,
        )

    if bert_model is None:
        logger.debug("BERT model not loaded — using heuristic quality scorer")
        return _heuristic_quality(text)

    t0 = time.perf_counter()

    try:
        # Tokenize
        if tokenizer is not None:
            # Real tokenizer from transformers
            encoded = tokenizer(
                text,
                max_length=128,
                padding="max_length",
                truncation=True,
                return_tensors="np",
            )
            input_ids = encoded["input_ids"].astype(np.int64)
            attention_mask = encoded["attention_mask"].astype(np.int64)
        else:
            input_ids, attention_mask = _simple_tokenize(text)

        # ONNX inference
        inputs = {}
        input_names = [inp.name for inp in bert_model.get_inputs()]
        if "input_ids" in input_names:
            inputs["input_ids"] = input_ids
        if "attention_mask" in input_names:
            inputs["attention_mask"] = attention_mask
        if "token_type_ids" in input_names:
            inputs["token_type_ids"] = np.zeros_like(input_ids)

        output_name = bert_model.get_outputs()[0].name
        logits = bert_model.run([output_name], inputs)[0]

        # Softmax
        logits = logits.squeeze()
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()

        # Map to quality labels
        probabilities: dict[str, float] = {}
        for i, label in enumerate(QUALITY_LABELS):
            if i < len(probs):
                probabilities[label] = round(float(probs[i]), 4)

        max_idx = int(np.argmax(probs))
        label = QUALITY_LABELS[max_idx] if max_idx < len(QUALITY_LABELS) else "average"
        confidence = float(probs[max_idx])

        # Interpolated base score
        base_score = sum(
            QUALITY_BASE_SCORES.get(k, 60.0) * v
            for k, v in probabilities.items()
        )

    except Exception as exc:
        logger.error("BERT text quality inference error: %s", exc)
        result = _heuristic_quality(text)
        result.inference_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        return result

    inference_ms = (time.perf_counter() - t0) * 1000.0

    result = TextQualityResult(
        label=label,
        probabilities=probabilities,
        confidence=round(confidence, 4),
        base_score=round(base_score, 1),
        inference_ms=round(inference_ms, 1),
    )

    logger.info(
        "TextQuality: %s (%.1f%% conf, base_score=%.1f, %.1fms)",
        label,
        confidence * 100,
        base_score,
        inference_ms,
    )

    return result
