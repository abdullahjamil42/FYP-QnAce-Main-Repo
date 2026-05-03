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

import json
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
    Scores on: length, STAR structure, specificity, connectives, filler penalty.
    """
    lower = text.lower()
    words = text.split()
    word_count = len(words)

    # --- Length score (sweet spot: 40-120 words) ---
    if word_count < 10:
        length_score = word_count / 10.0 * 0.3
    elif word_count <= 120:
        length_score = 0.3 + (word_count - 10) / 110.0 * 0.4
    else:
        length_score = 0.7  # very long answers get no extra credit

    # --- STAR method detection (Situation, Task, Action, Result) ---
    star_keywords = {
        "situation": ["situation", "context", "at the time", "when i was", "we were facing"],
        "task": ["task", "my responsibility", "i was responsible", "i needed to", "the goal was"],
        "action": ["action", "i decided", "i implemented", "i built", "i led", "i fixed",
                   "i refactored", "i designed", "i wrote", "i deployed", "so i"],
        "result": ["result", "outcome", "as a result", "this led to", "we achieved",
                   "reduced", "improved", "increased", "saved", "the impact was"],
    }
    star_hit = sum(
        1 for kws in star_keywords.values()
        if any(kw in lower for kw in kws)
    )
    star_score = star_hit / 4.0 * 0.25  # max 0.25

    # --- Specificity: numbers, names, tech terms ---
    has_numbers = any(c.isdigit() for c in text)
    tech_terms = ["api", "database", "cache", "latency", "throughput", "sql", "docker",
                  "kubernetes", "microservice", "algorithm", "complexity", "async", "thread",
                  "deploy", "ci/cd", "test", "sprint", "stakeholder", "metric", "sla"]
    tech_hits = sum(1 for t in tech_terms if t in lower)
    specificity_score = min((has_numbers * 0.05) + (tech_hits * 0.02), 0.15)

    # --- Logical connectives ---
    connectives = ["because", "therefore", "however", "although", "which meant",
                   "as a result", "consequently", "in order to", "this allowed",
                   "specifically", "for example", "for instance", "in particular"]
    connective_hits = sum(1 for c in connectives if c in lower)
    connective_score = min(connective_hits * 0.04, 0.12)

    # --- Filler penalty ---
    fillers = ["um", "uh", "like", "you know", "basically", "literally",
               "kind of", "sort of", "i mean", "actually"]
    filler_hits = sum(lower.count(f) for f in fillers)
    filler_penalty = min(filler_hits * 0.03, 0.12)

    # --- Final score ---
    raw_score = length_score + star_score + specificity_score + connective_score - filler_penalty
    raw_score = max(0.0, min(1.0, raw_score))

    if raw_score >= 0.62:
        probs = {"poor": 0.05, "average": 0.20, "excellent": 0.75}
        label = "excellent"
    elif raw_score >= 0.32:
        probs = {"poor": 0.15, "average": 0.65, "excellent": 0.20}
        label = "average"
    else:
        probs = {"poor": 0.70, "average": 0.25, "excellent": 0.05}
        label = "poor"

    base_score = sum(QUALITY_BASE_SCORES[k] * v for k, v in probs.items())

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


# ────────────────────────────────────────
# LLM-based text quality evaluation
# ────────────────────────────────────────

_LLM_EVAL_SYSTEM_PROMPT = """\
You are an interview answer quality evaluator. Given a candidate's spoken answer, \
rate it on a 0-100 scale and classify it as "poor", "average", or "excellent".

Scoring guide:
- poor (0-40): Off-topic, vague, no structure, very short, or incoherent.
- average (41-70): Addresses the question but lacks depth, specifics, or STAR structure.
- excellent (71-100): Clear, specific, well-structured (STAR), with measurable outcomes.

Respond with ONLY a JSON object, no other text:
{"score": <int 0-100>, "label": "<poor|average|excellent>"}"""


async def classify_quality_llm(text: str, settings: Any) -> TextQualityResult:
    """
    Evaluate interview answer quality using the configured LLM provider.

    Falls back to heuristic scoring on failure or timeout.
    """
    if not text or not text.strip():
        return TextQualityResult(
            label="poor",
            probabilities={"poor": 1.0, "average": 0.0, "excellent": 0.0},
            confidence=1.0,
            base_score=30.0,
        )

    t0 = time.perf_counter()

    try:
        import httpx

        base_url = getattr(settings, "local_llm_base_url", "http://localhost:8081")
        if not base_url.startswith(("http://", "https://")):
            logger.warning(
                "local_llm_base_url %r is missing an http/https scheme — prepending 'http://'. "
                "Fix LOCAL_LLM_BASE_URL in .env to silence this warning.",
                base_url,
            )
            base_url = "http://" + base_url
        url = f"{base_url.rstrip('/')}/v1/chat/completions"

        api_key = getattr(settings, "local_llm_api_key", "") or ""
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": getattr(settings, "local_llm_base_model", ""),
            "messages": [
                {"role": "system", "content": _LLM_EVAL_SYSTEM_PROMPT},
                {"role": "user", "content": f"Candidate's answer:\n\n{text}"},
            ],
            "temperature": 0.0,
            "max_tokens": 60,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            logger.warning("LLM quality eval HTTP %d, falling back to heuristic", response.status_code)
            return _heuristic_quality(text)

        body = response.json()
        content = ""
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            logger.warning("LLM quality eval: malformed response, falling back to heuristic")
            return _heuristic_quality(text)

        # Parse JSON from the LLM response
        parsed = _parse_llm_eval_json(content)
        if parsed is None:
            logger.warning("LLM quality eval: failed to parse '%s', falling back to heuristic", content[:100])
            return _heuristic_quality(text)

        score = max(0.0, min(100.0, float(parsed["score"])))
        label = str(parsed["label"]).lower()
        if label not in QUALITY_LABELS:
            if score >= 71:
                label = "excellent"
            elif score >= 41:
                label = "average"
            else:
                label = "poor"

        # Build probability distribution from score
        if label == "excellent":
            probs = {"poor": 0.05, "average": 0.15, "excellent": 0.80}
        elif label == "average":
            probs = {"poor": 0.15, "average": 0.70, "excellent": 0.15}
        else:
            probs = {"poor": 0.75, "average": 0.20, "excellent": 0.05}

        inference_ms = (time.perf_counter() - t0) * 1000.0

        result = TextQualityResult(
            label=label,
            probabilities=probs,
            confidence=probs[label],
            base_score=round(score, 1),
            inference_ms=round(inference_ms, 1),
        )

        logger.info(
            "TextQuality(LLM): %s (score=%.1f, %.1fms)",
            label, score, inference_ms,
        )
        return result

    except Exception as exc:
        inference_ms = (time.perf_counter() - t0) * 1000.0
        logger.warning("LLM quality eval failed (%.0fms): %s, falling back to heuristic", inference_ms, exc)
        result = _heuristic_quality(text)
        result.inference_ms = round(inference_ms, 1)
        return result


def _parse_llm_eval_json(text: str) -> Optional[dict]:
    """Extract {score, label} JSON from LLM response text."""
    raw = (text or "").strip()
    if not raw:
        return None

    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and "score" in obj and "label" in obj:
            return obj
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from surrounding text
    first = raw.find("{")
    last = raw.rfind("}")
    if first >= 0 and last > first:
        try:
            obj = json.loads(raw[first:last + 1])
            if isinstance(obj, dict) and "score" in obj and "label" in obj:
                return obj
        except json.JSONDecodeError:
            pass

    return None
