"""
Q&Ace — Wav2Vec2 Vocal Emotion Analysis.

Architecture per ADR-007/ADR-008:
  - Wav2Vec2 FP16 on GPU via MPS (fits in Whisper's SM gaps).
  - Runs inside ProcessPoolExecutor worker (parallel with STT).
  - Input: int16 numpy array @ 16 kHz.
  - Output: VocalResult with pitch, energy, emotion probabilities, confidence.
  - Target: ~60ms on RTX 4090 for 7.5s audio.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("qace.vocal")

# Emotion labels from wav2vec2-large-robust-12-ft-emotion-msp-dim model
EMOTION_LABELS = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]

# Simplified labels for interview context
INTERVIEW_EMOTIONS = {
    "angry": "tense",
    "disgusted": "uncomfortable",
    "fearful": "nervous",
    "happy": "confident",
    "neutral": "composed",
    "sad": "uncertain",
    "surprised": "engaged",
}


@dataclass
class VocalResult:
    """Result from Wav2Vec2 vocal analysis."""
    dominant_emotion: str = "neutral"
    emotion_probs: dict[str, float] = field(default_factory=dict)
    acoustic_confidence: float = 0.0  # 0-1, how confident the model is in its prediction
    pitch_mean_hz: float = 0.0
    pitch_std_hz: float = 0.0
    energy_rms: float = 0.0
    energy_db: float = 0.0
    speech_rate_factor: float = 1.0  # relative to normal (~3.5 syllables/sec)
    inference_ms: float = 0.0


def compute_pitch_features(audio_f32: np.ndarray, sr: int = 16_000) -> tuple[float, float]:
    """
    Estimate pitch using autocorrelation (no external deps).

    Returns (mean_hz, std_hz). Simple but sufficient for interview assessment.
    """
    frame_len = int(0.03 * sr)  # 30ms frames
    hop = int(0.01 * sr)  # 10ms hop
    min_lag = int(sr / 500)  # 500 Hz max pitch
    max_lag = int(sr / 60)  # 60 Hz min pitch

    pitches = []
    for start in range(0, len(audio_f32) - frame_len, hop):
        frame = audio_f32[start : start + frame_len]
        # Skip silent frames
        if np.max(np.abs(frame)) < 0.01:
            continue

        # Autocorrelation
        corr = np.correlate(frame, frame, mode="full")
        corr = corr[len(corr) // 2 :]  # keep positive lags

        if max_lag >= len(corr):
            continue

        # Find peak in valid pitch range
        search_region = corr[min_lag:max_lag]
        if len(search_region) == 0:
            continue

        peak_idx = np.argmax(search_region) + min_lag
        if corr[peak_idx] > 0.3 * corr[0]:  # voiced threshold
            pitch_hz = sr / peak_idx
            if 60 <= pitch_hz <= 500:
                pitches.append(pitch_hz)

    if not pitches:
        return 0.0, 0.0

    return float(np.mean(pitches)), float(np.std(pitches))


def compute_energy_features(audio_f32: np.ndarray) -> tuple[float, float]:
    """Compute RMS energy and dB level."""
    rms = float(np.sqrt(np.mean(audio_f32 ** 2)))
    db = float(20 * np.log10(max(rms, 1e-10)))
    return rms, db


def analyze(audio: np.ndarray, vocal_model: Any) -> VocalResult:
    """
    Analyze vocal features from int16 @ 16 kHz audio using Wav2Vec2.

    Falls back to acoustic-only analysis if model is unavailable.
    """
    # Convert int16 → float32 [-1, 1]
    audio_f32 = audio.astype(np.float32) / 32768.0
    duration_s = len(audio_f32) / 16_000

    # Always compute acoustic features (no model needed)
    pitch_mean, pitch_std = compute_pitch_features(audio_f32)
    energy_rms, energy_db = compute_energy_features(audio_f32)

    if vocal_model is None:
        logger.debug("Wav2Vec2 model not loaded — returning acoustic-only result")
        return VocalResult(
            dominant_emotion="neutral",
            emotion_probs={"neutral": 1.0},
            acoustic_confidence=0.0,
            pitch_mean_hz=round(pitch_mean, 1),
            pitch_std_hz=round(pitch_std, 1),
            energy_rms=round(energy_rms, 4),
            energy_db=round(energy_db, 1),
        )

    t0 = time.perf_counter()

    try:
        import torch

        def _run_model(model: Any, device: Any) -> np.ndarray:
            param = next(model.parameters())
            input_dtype = param.dtype if torch.is_floating_point(param) else torch.float32
            inputs = torch.tensor(audio_f32, dtype=input_dtype).unsqueeze(0).to(device=device, dtype=input_dtype)
            with torch.no_grad():
                outputs = model(inputs)
            logits = outputs.logits if hasattr(outputs, "logits") else outputs[0]
            return torch.nn.functional.softmax(logits, dim=-1).squeeze().cpu().numpy()

        device = next(vocal_model.parameters()).device
        try:
            probs = _run_model(vocal_model, device)
        except Exception as exc:
            if device.type != "cuda":
                raise
            logger.warning("Wav2Vec2 GPU inference failed (%s) — retrying on CPU", exc)
            vocal_model = vocal_model.to("cpu").float().eval()
            probs = _run_model(vocal_model, torch.device("cpu"))

        emotion_probs = {}
        for i, label in enumerate(EMOTION_LABELS):
            if i < len(probs):
                mapped = INTERVIEW_EMOTIONS.get(label, label)
                emotion_probs[mapped] = round(float(probs[i]), 4)

        max_idx = int(np.argmax(probs))
        raw_label = EMOTION_LABELS[max_idx] if max_idx < len(EMOTION_LABELS) else "neutral"
        dominant = INTERVIEW_EMOTIONS.get(raw_label, raw_label)
        confidence = float(probs[max_idx]) if max_idx < len(probs) else 0.0

    except Exception as exc:
        logger.error("Wav2Vec2 inference error: %s", exc)
        emotion_probs = {"neutral": 1.0}
        dominant = "neutral"
        confidence = 0.0

    inference_ms = (time.perf_counter() - t0) * 1000.0

    result = VocalResult(
        dominant_emotion=dominant,
        emotion_probs=emotion_probs,
        acoustic_confidence=round(confidence, 4),
        pitch_mean_hz=round(pitch_mean, 1),
        pitch_std_hz=round(pitch_std, 1),
        energy_rms=round(energy_rms, 4),
        energy_db=round(energy_db, 1),
        inference_ms=round(inference_ms, 1),
    )

    logger.info(
        "Vocal: %s (%.1f%% conf, pitch=%.0fHz, energy=%.1fdB, %.0fms)",
        dominant,
        confidence * 100,
        pitch_mean,
        energy_db,
        inference_ms,
    )

    return result
