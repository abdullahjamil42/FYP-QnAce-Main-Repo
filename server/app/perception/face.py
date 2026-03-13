"""
Q&Ace — EfficientNet-B2 Face Emotion Classifier (ONNX, CPU).

Architecture per ADR-003:
  - EfficientNet-B2 runs on CPU ONNX to avoid GPU contention.
  - Input: 224×224 RGB face crop (uint8 numpy array).
  - Output: FaceResult with emotion classification + probabilities.
  - Target: <5ms per inference on CPU.
  - Model source: `abdullahjamil42/QnAce-Face-Model`
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("qace.face")

# Emotion labels for our custom-trained EfficientNet-B2
# These map to interview-relevant emotional states
FACE_EMOTION_LABELS = [
    "angry",
    "disgusted",
    "fearful",
    "happy",
    "neutral",
    "sad",
    "surprised",
]

# Map raw labels to interview context
INTERVIEW_FACE_EMOTIONS = {
    "angry": "tense",
    "disgusted": "uncomfortable",
    "fearful": "nervous",
    "happy": "positive",
    "neutral": "composed",
    "sad": "uncertain",
    "surprised": "engaged",
}

# ImageNet normalization (EfficientNet)
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass
class FaceResult:
    """Result from EfficientNet-B2 face emotion classification."""
    dominant_emotion: str = "neutral"
    emotion_probs: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    inference_ms: float = 0.0


def preprocess_face(image: np.ndarray) -> np.ndarray:
    """
    Preprocess a face crop for EfficientNet-B2 inference.

    Input: HWC uint8 RGB image (ideally 224×224).
    Output: NCHW float32 tensor, ImageNet-normalized.
    """
    # Resize to 224×224 if needed (bilinear, no scipy/PIL)
    if image.shape[:2] != (224, 224):
        image = _resize_bilinear(image, 224, 224)

    # uint8 → float32 [0, 1]
    img_f32 = image.astype(np.float32) / 255.0

    # ImageNet normalize
    img_f32 = (img_f32 - IMAGENET_MEAN) / IMAGENET_STD

    # HWC → CHW → NCHW
    img_f32 = np.transpose(img_f32, (2, 0, 1))  # CHW
    img_f32 = np.expand_dims(img_f32, axis=0)  # NCHW

    return img_f32


def _resize_bilinear(image: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Simple bilinear resize without external dependencies."""
    h, w = image.shape[:2]
    if h == target_h and w == target_w:
        return image

    row_indices = np.linspace(0, h - 1, target_h)
    col_indices = np.linspace(0, w - 1, target_w)

    row_floor = np.floor(row_indices).astype(int)
    row_ceil = np.minimum(row_floor + 1, h - 1)
    row_frac = row_indices - row_floor

    col_floor = np.floor(col_indices).astype(int)
    col_ceil = np.minimum(col_floor + 1, w - 1)
    col_frac = col_indices - col_floor

    # Bilinear interpolation
    result = np.zeros((target_h, target_w, image.shape[2] if image.ndim == 3 else 1), dtype=image.dtype)
    for i in range(target_h):
        for j in range(target_w):
            rf, rc = row_floor[i], row_ceil[i]
            cf, cc = col_floor[j], col_ceil[j]
            ry, rx = row_frac[i], col_frac[j]

            val = (
                image[rf, cf] * (1 - ry) * (1 - rx)
                + image[rf, cc] * (1 - ry) * rx
                + image[rc, cf] * ry * (1 - rx)
                + image[rc, cc] * ry * rx
            )
            result[i, j] = val

    return result


def classify(face_crop: np.ndarray, face_model: Any) -> FaceResult:
    """
    Classify face emotion from a 224×224 RGB crop using EfficientNet-B2 ONNX.

    Falls back to neutral if model is unavailable.
    """
    if face_model is None:
        logger.debug("Face model not loaded — returning neutral result")
        return FaceResult(
            dominant_emotion="neutral",
            emotion_probs={"composed": 1.0},
            confidence=0.0,
        )

    if face_crop is None or face_crop.size == 0:
        return FaceResult(
            dominant_emotion="neutral",
            emotion_probs={"composed": 1.0},
            confidence=0.0,
        )

    t0 = time.perf_counter()

    try:
        # Preprocess
        input_tensor = preprocess_face(face_crop)

        # ONNX inference — always CPU (per ADR-003)
        input_name = face_model.get_inputs()[0].name
        output_name = face_model.get_outputs()[0].name
        logits = face_model.run([output_name], {input_name: input_tensor})[0]

        # Softmax
        logits = logits.squeeze()
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()

        # Map to emotion labels
        emotion_probs: dict[str, float] = {}
        for i, label in enumerate(FACE_EMOTION_LABELS):
            if i < len(probs):
                mapped = INTERVIEW_FACE_EMOTIONS.get(label, label)
                # Accumulate if same mapped label
                emotion_probs[mapped] = emotion_probs.get(mapped, 0.0) + round(float(probs[i]), 4)

        max_idx = int(np.argmax(probs))
        raw_label = FACE_EMOTION_LABELS[max_idx] if max_idx < len(FACE_EMOTION_LABELS) else "neutral"
        dominant = INTERVIEW_FACE_EMOTIONS.get(raw_label, raw_label)
        confidence = float(probs[max_idx])

    except Exception as exc:
        logger.error("EfficientNet inference error: %s", exc)
        emotion_probs = {"composed": 1.0}
        dominant = "neutral"
        confidence = 0.0

    inference_ms = (time.perf_counter() - t0) * 1000.0

    result = FaceResult(
        dominant_emotion=dominant,
        emotion_probs=emotion_probs,
        confidence=round(confidence, 4),
        inference_ms=round(inference_ms, 1),
    )

    logger.info(
        "Face: %s (%.1f%% conf, %.1fms)",
        dominant,
        confidence * 100,
        inference_ms,
    )

    return result
