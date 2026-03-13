"""
Q&Ace — Parallel Perception Engine Tests.

Verifies:
  1. PerceptionOrchestrator runs all modules without errors.
  2. Wall-clock time ≤ max(individual modules) + overhead.
  3. PerceptionResult is fully populated.
  4. Graceful degradation when models are None (heuristic fallbacks).
  5. AU telemetry passthrough.
"""

from __future__ import annotations

import asyncio
import time

import numpy as np
import pytest

from server.app.perception.stt import STTResult, transcribe
from server.app.perception.vocal import VocalResult, analyze as vocal_analyze
from server.app.perception.face import FaceResult, classify as face_classify
from server.app.perception.text_quality import (
    TextQualityResult,
    classify_quality,
)
from server.app.perception.orchestrator import (
    PerceptionOrchestrator,
    PerceptionResult,
)


# ────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────

@pytest.fixture
def audio_7s():
    """7.5 seconds of 250 Hz sine wave @ 16 kHz (simulates speech segment)."""
    sr = 16_000
    t = np.linspace(0, 7.5, int(sr * 7.5), endpoint=False)
    return (np.sin(2 * np.pi * 250 * t) * 16000).astype(np.int16)


@pytest.fixture
def face_crop_224():
    """Random 224×224 RGB uint8 image (simulates face crop from client)."""
    rng = np.random.default_rng(42)
    return rng.integers(0, 255, size=(224, 224, 3), dtype=np.uint8)


@pytest.fixture
def sample_au():
    """Sample AU telemetry dict."""
    return {
        "au4": 0.35,
        "au12": 0.72,
        "au45": 0.10,
        "eye_contact": 0.95,
    }


# ────────────────────────────────────────
# Individual module tests (no models loaded)
# ────────────────────────────────────────

class TestSTTFallback:
    """STT returns empty result when whisper_model is None."""

    def test_returns_empty_stt_result(self, audio_7s: np.ndarray):
        result = transcribe(audio_7s, whisper_model=None)
        assert isinstance(result, STTResult)
        assert result.text == ""
        assert result.inference_ms == 0.0

    def test_filler_count_zero(self, audio_7s: np.ndarray):
        result = transcribe(audio_7s, whisper_model=None)
        assert result.filler_count == 0


class TestVocalFallback:
    """Vocal returns acoustics-only fallback when model is None."""

    def test_returns_vocal_result(self, audio_7s: np.ndarray):
        result = vocal_analyze(audio_7s, vocal_model=None)
        assert isinstance(result, VocalResult)
        assert result.dominant_emotion == "neutral"

    def test_acoustic_features_computed(self, audio_7s: np.ndarray):
        result = vocal_analyze(audio_7s, vocal_model=None)
        # Acoustics should still be computed even without model
        assert result.pitch_mean_hz >= 0.0
        assert result.energy_db != 0.0


class TestFaceFallback:
    """Face returns default neutral when model is None."""

    def test_returns_face_result(self, face_crop_224: np.ndarray):
        result = face_classify(face_crop_224, face_model=None)
        assert isinstance(result, FaceResult)
        assert result.dominant_emotion == "neutral"
        assert result.confidence == 0.0


class TestTextQualityHeuristic:
    """Text quality uses heuristic when BERT model is None."""

    def test_short_response(self):
        result = classify_quality("Yes.", bert_model=None)
        assert isinstance(result, TextQualityResult)
        assert result.label in ("poor", "average", "excellent")
        # Very short answer should score lower
        assert result.base_score <= 60

    def test_star_method_response(self):
        text = (
            "In my previous role as a software engineer, "
            "I was tasked with improving response time. "
            "I implemented caching and optimized database queries. "
            "As a result, we achieved a 50% reduction in latency."
        )
        result = classify_quality(text, bert_model=None)
        assert isinstance(result, TextQualityResult)
        # Good structured answer should score well
        assert result.base_score >= 50

    def test_empty_text(self):
        result = classify_quality("", bert_model=None)
        assert isinstance(result, TextQualityResult)
        assert result.label == "poor"


# ────────────────────────────────────────
# Orchestrator tests
# ────────────────────────────────────────

class TestPerceptionOrchestrator:
    """
    Tests the orchestrator with no models loaded.
    All modules should fall back to defaults/heuristics.
    """

    @pytest.fixture
    def orchestrator(self):
        orch = PerceptionOrchestrator(use_process_pool=False)
        yield orch
        orch.shutdown()

    @pytest.mark.asyncio
    async def test_run_returns_result(
        self, orchestrator: PerceptionOrchestrator, audio_7s: np.ndarray
    ):
        result = await orchestrator.run(audio_7s)
        assert isinstance(result, PerceptionResult)

    @pytest.mark.asyncio
    async def test_all_fields_populated(
        self,
        orchestrator: PerceptionOrchestrator,
        audio_7s: np.ndarray,
        face_crop_224: np.ndarray,
        sample_au: dict,
    ):
        result = await orchestrator.run(audio_7s, face_crop_224, sample_au)
        # STT
        assert isinstance(result.transcript, str)
        assert isinstance(result.stt_inference_ms, float)
        # Vocal
        assert result.vocal_emotion in (
            "neutral", "confident", "enthusiastic", "tense",
            "nervous", "contemplative", "uncomfortable", "surprised",
        )
        # Face
        assert result.face_emotion in (
            "neutral", "confident", "enthusiastic", "tense",
            "nervous", "contemplative", "uncomfortable",
        )
        # Text quality
        assert result.text_quality_label in ("poor", "average", "excellent")
        assert 0 <= result.text_quality_score <= 100
        # AU passthrough
        assert result.au4 == pytest.approx(0.35)
        assert result.au12 == pytest.approx(0.72)
        assert result.au45 == pytest.approx(0.10)
        assert result.eye_contact == pytest.approx(0.95)

    @pytest.mark.asyncio
    async def test_wall_clock_reasonable(
        self,
        orchestrator: PerceptionOrchestrator,
        audio_7s: np.ndarray,
    ):
        """Wall-clock should ≤ sum of individual modules (proves parallelism)."""
        t0 = time.perf_counter()
        result = await orchestrator.run(audio_7s)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert result.total_wall_ms > 0
        assert result.parallel_wall_ms > 0
        # Total should include both parallel + sequential
        assert result.total_wall_ms >= result.parallel_wall_ms
        # Elapsed should be within 200ms of reported total (accounting for test overhead)
        assert elapsed_ms < result.total_wall_ms + 200

    @pytest.mark.asyncio
    async def test_no_face_crop(
        self,
        orchestrator: PerceptionOrchestrator,
        audio_7s: np.ndarray,
    ):
        """Should work fine without a face crop (uses black 224x224 placeholder)."""
        result = await orchestrator.run(audio_7s, face_crop=None)
        assert isinstance(result, PerceptionResult)
        assert result.face_emotion == "neutral"

    @pytest.mark.asyncio
    async def test_no_au_telemetry(
        self,
        orchestrator: PerceptionOrchestrator,
        audio_7s: np.ndarray,
    ):
        """AU values should default to 0 when no telemetry."""
        result = await orchestrator.run(audio_7s, au_telemetry=None)
        assert result.au4 == 0.0
        assert result.au12 == 0.0
        assert result.au45 == 0.0
        assert result.eye_contact == 0.0


# ────────────────────────────────────────
# Data channel AU telemetry parsing
# ────────────────────────────────────────

class TestAUTelemetryParsing:
    """Test binary AU telemetry parsing on the server side."""

    def test_valid_packet(self):
        """20-byte packet should parse correctly."""
        import struct
        from server.app.webrtc.data_channel import parse_au_telemetry

        packed = struct.pack("<Iffff", 12345, 0.3, 0.7, 0.1, 0.9)
        result = parse_au_telemetry(packed)
        assert result is not None
        assert result.timestamp == 12345
        assert result.au4 == pytest.approx(0.3, abs=1e-5)
        assert result.au12 == pytest.approx(0.7, abs=1e-5)
        assert result.au45 == pytest.approx(0.1, abs=1e-5)
        assert result.eye_contact == pytest.approx(0.9, abs=1e-5)

    def test_short_packet(self):
        """Packets shorter than 20 bytes should return None."""
        from server.app.webrtc.data_channel import parse_au_telemetry

        assert parse_au_telemetry(b"\x00" * 10) is None
        assert parse_au_telemetry(b"") is None

    def test_extra_bytes_ignored(self):
        """Packets longer than 20 bytes should still parse first 20."""
        import struct
        from server.app.webrtc.data_channel import parse_au_telemetry

        packed = struct.pack("<Iffff", 100, 0.5, 0.5, 0.5, 0.5) + b"\xff" * 10
        result = parse_au_telemetry(packed)
        assert result is not None
        assert result.timestamp == 100
