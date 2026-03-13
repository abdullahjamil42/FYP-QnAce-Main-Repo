"""
Q&Ace — VAD Unit Tests.

Tests for:
  - Ring buffer read/write correctness
  - End-of-speech detector with energy-based fallback
  - Speech / silence boundary detection
"""

from __future__ import annotations

import numpy as np
import pytest

from server.app.vad.ring_buffer import RingBuffer
from server.app.vad.silero import EndOfSpeechDetector, SAMPLE_RATE


# ────────────────────────────────────────
# Ring Buffer Tests
# ────────────────────────────────────────

class TestRingBuffer:
    def test_write_and_read(self):
        rb = RingBuffer(max_seconds=1.0, sample_rate=16_000)
        data = np.arange(8000, dtype=np.int16)
        rb.write(data)
        result = rb.read_last(8000)
        np.testing.assert_array_equal(result, data)

    def test_wraparound(self):
        rb = RingBuffer(max_seconds=1.0, sample_rate=16_000)
        # Write 1.5× capacity
        data = np.arange(24_000, dtype=np.int16)
        rb.write(data)
        result = rb.read_last(16_000)
        np.testing.assert_array_equal(result, data[-16_000:])

    def test_read_last_seconds(self):
        rb = RingBuffer(max_seconds=5.0, sample_rate=16_000)
        data = np.ones(48_000, dtype=np.int16)  # 3 seconds
        rb.write(data)
        result = rb.read_last_seconds(2.0)
        assert len(result) == 32_000

    def test_empty_read(self):
        rb = RingBuffer(max_seconds=1.0, sample_rate=16_000)
        result = rb.read_last(100)
        assert len(result) == 0

    def test_clear(self):
        rb = RingBuffer(max_seconds=1.0, sample_rate=16_000)
        rb.write(np.ones(1000, dtype=np.int16))
        rb.clear()
        assert rb.available_seconds == 0.0


# ────────────────────────────────────────
# End-of-Speech Detector Tests
# ────────────────────────────────────────

class TestEndOfSpeechDetector:
    def test_silero_merged_state_signature_supported(self):
        """Newer Silero ONNX exports use a single 'state' tensor instead of h/c."""

        class _FakeIO:
            def __init__(self, name, shape):
                self.name = name
                self.shape = shape

        class _FakeSession:
            def get_inputs(self):
                return [
                    _FakeIO("input", [None, None]),
                    _FakeIO("state", [2, None, 128]),
                    _FakeIO("sr", []),
                ]

            def get_outputs(self):
                return [
                    _FakeIO("output", [None, 1]),
                    _FakeIO("stateN", [None, None, None]),
                ]

            def run(self, _output_names, ort_inputs):
                assert "state" in ort_inputs
                assert ort_inputs["state"].shape == (2, 1, 128)
                return np.array([[0.9]], dtype=np.float32), ort_inputs["state"]

        det = EndOfSpeechDetector(silero_session=_FakeSession())
        speech = (np.ones(512, dtype=np.float32) * 5000).astype(np.int16)
        assert det._silero_detect(speech) is True

    def test_speech_triggers_callback(self, sample_audio_speech):
        """Loud audio followed by silence should trigger EOS."""
        fired = []

        def on_eos(audio):
            fired.append(len(audio))

        det = EndOfSpeechDetector(
            silence_ms=200,
            min_speech_s=0.3,
            on_speech_end=on_eos,
        )

        # Feed speech in 32ms chunks
        chunk_size = 512
        for i in range(0, len(sample_audio_speech), chunk_size):
            det.feed(sample_audio_speech[i : i + chunk_size])

        # Feed silence to trigger EOS
        silence = np.zeros(int(0.3 * SAMPLE_RATE), dtype=np.int16)
        for i in range(0, len(silence), chunk_size):
            det.feed(silence[i : i + chunk_size])

        assert len(fired) >= 1, "EOS should have fired after speech + silence"

    def test_silence_only_no_callback(self, sample_audio_silence):
        """Pure silence should never trigger EOS."""
        fired = []

        det = EndOfSpeechDetector(
            silence_ms=200,
            min_speech_s=0.5,
            on_speech_end=lambda a: fired.append(1),
        )

        chunk_size = 512
        for i in range(0, len(sample_audio_silence), chunk_size):
            det.feed(sample_audio_silence[i : i + chunk_size])

        assert len(fired) == 0, "EOS should NOT fire for pure silence"

    def test_short_speech_ignored(self):
        """Speech shorter than min_speech_s should be ignored."""
        fired = []

        det = EndOfSpeechDetector(
            silence_ms=100,
            min_speech_s=1.0,  # require at least 1s
            on_speech_end=lambda a: fired.append(1),
        )

        # 0.2s of loud audio
        short = (np.sin(np.linspace(0, 100, 3200)) * 20000).astype(np.int16)
        det.feed(short)
        # Silence
        det.feed(np.zeros(3200, dtype=np.int16))

        assert len(fired) == 0, "Short speech should be filtered out"

    def test_flush(self, sample_audio_speech):
        """Flush should fire EOS for buffered speech."""
        fired = []

        det = EndOfSpeechDetector(
            silence_ms=200,
            min_speech_s=0.3,
            on_speech_end=lambda a: fired.append(len(a)),
        )

        det.feed(sample_audio_speech)
        det.flush()

        assert len(fired) >= 1, "Flush should trigger EOS for buffered speech"

    def test_small_chunks_accumulate_before_detection(self):
        """320-sample WebRTC frames must accumulate to 512 before Silero runs."""

        class _FakeIO:
            def __init__(self, name, shape):
                self.name = name
                self.shape = shape

        calls = []

        class _FakeSession:
            def get_inputs(self):
                return [
                    _FakeIO("input", [None, None]),
                    _FakeIO("state", [2, None, 128]),
                    _FakeIO("sr", []),
                ]

            def get_outputs(self):
                return [
                    _FakeIO("output", [None, 1]),
                    _FakeIO("stateN", [None, None, None]),
                ]

            def run(self, _output_names, ort_inputs):
                calls.append(ort_inputs["input"].shape)
                return np.array([[0.9]], dtype=np.float32), ort_inputs["state"]

        det = EndOfSpeechDetector(silero_session=_FakeSession())

        # Feed 320-sample chunks (simulating 48→16 kHz resampled WebRTC frames)
        chunk = (np.ones(320, dtype=np.float32) * 5000).astype(np.int16)
        det.feed(chunk)  # 320 pending — no Silero call yet
        assert len(calls) == 0, "Should not call Silero with only 320 samples"

        det.feed(chunk)  # 640 pending → 1 call (512 consumed, 128 remain)
        assert len(calls) == 1, "Should call Silero once after 640 samples"
        assert calls[0] == (1, 512), "Silero must receive exactly (1, 512)"

        det.feed(chunk)  # 128 + 320 = 448 pending — no call
        assert len(calls) == 1

        det.feed(chunk)  # 448 + 320 = 768 → 1 more call (512 consumed, 256 remain)
        assert len(calls) == 2
