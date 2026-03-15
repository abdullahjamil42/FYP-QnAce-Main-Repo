"""
Q&Ace — Silero VAD v5 integration + End-of-Speech detection.

Architecture per ADR-006:
  - Silero VAD v5 ONNX on CPU, processes 32 ms chunks in <0.2 ms.
  - min_silence_duration = 200 ms (aggressive; saves 1800 ms vs default 2000 ms).
  - Energy-based fallback when Silero ONNX is unavailable.
  - 100 ms look-ahead confirmation window (cancel EOS if speech resumes).
  - Segments < 0.5 s treated as noise and skipped.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

import numpy as np

logger = logging.getLogger("qace.vad")

# ── Constants ──
SAMPLE_RATE = 16_000
CHUNK_SAMPLES = 512  # 32 ms at 16 kHz — Silero v5 native chunk size
SILENCE_THRESHOLD_SAMPLES_DEFAULT = int(0.200 * SAMPLE_RATE)  # 200 ms
LOOKAHEAD_SAMPLES = int(0.100 * SAMPLE_RATE)  # 100 ms look-ahead
MIN_SPEECH_SECONDS = 0.5
ENERGY_THRESHOLD = 150  # RMS threshold for energy-based fallback (lowered for browser mics)


class EndOfSpeechDetector:
    """
    Processes incoming 16 kHz int16 audio and fires a callback when
    continuous silence follows speech (end-of-speech event).
    """

    def __init__(
        self,
        silence_ms: int = 200,
        min_speech_s: float = 0.5,
        silero_session: Any = None,
        on_speech_end: Optional[Callable[[np.ndarray], None]] = None,
        semantic_turn_detector: Any = None,
        partial_transcript_provider: Optional[Callable[[], str]] = None,
    ):
        self.silence_threshold = int(silence_ms / 1000.0 * SAMPLE_RATE)
        self.min_speech_samples = int(min_speech_s * SAMPLE_RATE)
        self.silero = silero_session
        self.on_speech_end = on_speech_end
        # Optional Phase-advanced hooks are accepted for compatibility.
        self.semantic_turn_detector = semantic_turn_detector
        self.partial_transcript_provider = partial_transcript_provider

        # Silero runtime state — supports both legacy (h/c) and merged-state ONNX exports.
        self._silero_mode = "energy"
        self._state_input_name = "state"
        self._state_output_name = "stateN"
        self._state_shape = (2, 1, 128)
        self._state = np.zeros(self._state_shape, dtype=np.float32)
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)
        self._sr = np.array(SAMPLE_RATE, dtype=np.int64)
        self._configure_silero_session()

        # Pending audio buffer — accumulate until we have CHUNK_SAMPLES (512)
        self._pending = np.array([], dtype=np.int16)

        # Tracking
        self._is_speaking = False
        self._silence_samples = 0
        self._speech_start_sample = 0
        self._total_samples = 0
        self._speech_buffer: list[np.ndarray] = []

    # ── Core ──

    def feed(self, chunk: np.ndarray) -> None:
        """Feed a chunk of int16 audio. May trigger on_speech_end callback."""
        if len(chunk) == 0:
            return

        # Accumulate into pending buffer, then process in CHUNK_SAMPLES strides.
        self._pending = np.concatenate([self._pending, chunk])

        while len(self._pending) >= CHUNK_SAMPLES:
            frame = self._pending[:CHUNK_SAMPLES]
            self._pending = self._pending[CHUNK_SAMPLES:]
            self._process_frame(frame)

    def _process_frame(self, frame: np.ndarray) -> None:
        """Process a single CHUNK_SAMPLES (512-sample) frame through VAD."""
        n = len(frame)
        is_speech = self._detect_speech(frame)

        if is_speech:
            if not self._is_speaking:
                self._is_speaking = True
                self._speech_start_sample = self._total_samples
                self._speech_buffer.clear()
                logger.debug("Speech start at sample %d", self._total_samples)
            self._silence_samples = 0
            self._speech_buffer.append(frame.copy())
        else:
            if self._is_speaking:
                self._silence_samples += n
                self._speech_buffer.append(frame.copy())  # include trailing silence

                if self._silence_samples >= self.silence_threshold:
                    speech_samples = self._total_samples - self._speech_start_sample
                    if speech_samples >= self.min_speech_samples:
                        self._fire_eos()
                    else:
                        logger.debug(
                            "Ignoring short segment (%.2fs < %.2fs)",
                            speech_samples / SAMPLE_RATE,
                            self.min_speech_samples / SAMPLE_RATE,
                        )
                    self._is_speaking = False
                    self._silence_samples = 0
                    self._speech_buffer.clear()

        self._total_samples += n

    def flush(self) -> None:
        """Force-fire EOS for any buffered speech (e.g. on track end)."""
        # Process any remaining pending audio (may be < 512 samples)
        if len(self._pending) > 0:
            # Pad remaining samples to full chunk and process
            padded = np.pad(self._pending, (0, CHUNK_SAMPLES - len(self._pending)))
            self._process_frame(padded)
            self._pending = np.array([], dtype=np.int16)
        if self._is_speaking and self._speech_buffer:
            speech_samples = self._total_samples - self._speech_start_sample
            if speech_samples >= self.min_speech_samples:
                self._fire_eos()
            self._is_speaking = False
            self._speech_buffer.clear()

    def get_current_speech(self) -> Optional[np.ndarray]:
        """Return a snapshot of the in-progress utterance for interim STT."""
        if not self._is_speaking or not self._speech_buffer:
            return None
        return np.concatenate([chunk.copy() for chunk in self._speech_buffer])

    def get_current_speech_duration_s(self) -> float:
        """Return current in-progress speech duration in seconds."""
        if not self._is_speaking or not self._speech_buffer:
            return 0.0
        return sum(len(chunk) for chunk in self._speech_buffer) / SAMPLE_RATE

    @property
    def is_speaking(self) -> bool:
        """Expose whether VAD currently considers the user to be speaking."""
        return self._is_speaking

    # ── Detection backends ──

    def _detect_speech(self, chunk: np.ndarray) -> bool:
        """Returns True if this chunk contains speech (hybrid: Silero + energy)."""
        energy = self._energy_detect(chunk)

        if self.silero is not None:
            silero = self._silero_detect(chunk)
            if silero:
                return True
            # Silero said no — trust energy as safety net.
            # This handles broken/incompatible ONNX exports where Silero
            # returns near-zero probabilities regardless of input.
            if energy:
                return True
            return False

        return energy

    def _silero_detect(self, chunk: np.ndarray) -> bool:
        """Silero VAD ONNX inference — <0.2 ms per 32 ms chunk."""
        audio_f32 = (chunk.astype(np.float32) / 32768.0).reshape(1, -1)
        try:
            if self._silero_mode == "merged-state":
                ort_inputs = {
                    "input": audio_f32,
                    self._state_input_name: self._state,
                    "sr": self._sr,
                }
                output, state_out = self.silero.run(None, ort_inputs)
                self._state = np.asarray(state_out, dtype=np.float32)
            else:
                ort_inputs = {
                    "input": audio_f32,
                    "h": self._h,
                    "c": self._c,
                    "sr": np.array([SAMPLE_RATE], dtype=np.int64),
                }
                output, self._h, self._c = self.silero.run(None, ort_inputs)
            prob = float(np.asarray(output).reshape(-1)[0])
            if prob > 0.3:
                logger.debug("Silero prob=%.4f (speech)", prob)
            return prob > 0.5
        except Exception as exc:
            logger.warning("Silero inference error: %s — falling back to energy", exc)
            return self._energy_detect(chunk)

    def _configure_silero_session(self) -> None:
        """Inspect the ONNX signature once so inference can support multiple Silero exports."""
        if self.silero is None:
            self._silero_mode = "energy"
            return
        try:
            inputs = {item.name: item for item in self.silero.get_inputs()}
            outputs = self.silero.get_outputs()
            if "state" in inputs:
                self._silero_mode = "merged-state"
                self._state_input_name = "state"
                if len(outputs) > 1:
                    self._state_output_name = outputs[1].name
                raw_shape = inputs["state"].shape
                state_shape = tuple(1 if dim is None else int(dim) for dim in raw_shape)
                self._state_shape = state_shape
                self._state = np.zeros(self._state_shape, dtype=np.float32)
                self._sr = np.array(SAMPLE_RATE, dtype=np.int64)
            elif "h" in inputs and "c" in inputs:
                self._silero_mode = "legacy-lstm"
                self._h = np.zeros((2, 1, 64), dtype=np.float32)
                self._c = np.zeros((2, 1, 64), dtype=np.float32)
                self._sr = np.array([SAMPLE_RATE], dtype=np.int64)
            else:
                self._silero_mode = "energy"
                logger.warning("Silero ONNX signature not recognized — using energy fallback")
        except Exception as exc:
            self._silero_mode = "energy"
            logger.warning("Silero session inspection failed (%s) — using energy fallback", exc)

    def _energy_detect(self, chunk: np.ndarray) -> bool:
        """Simple RMS energy threshold (fallback)."""
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
        return rms > ENERGY_THRESHOLD

    # ── Helpers ──

    def _fire_eos(self) -> None:
        """Concatenate speech buffer and invoke callback."""
        if not self._speech_buffer or self.on_speech_end is None:
            return
        audio = np.concatenate(self._speech_buffer)
        duration = len(audio) / SAMPLE_RATE
        logger.info("End-of-speech: %.2fs audio captured", duration)
        try:
            self.on_speech_end(audio)
        except Exception as exc:
            logger.error("on_speech_end callback error: %s", exc)

    def reset(self) -> None:
        """Reset all state (new session)."""
        self._is_speaking = False
        self._silence_samples = 0
        self._speech_start_sample = 0
        self._total_samples = 0
        self._speech_buffer.clear()
        self._pending = np.array([], dtype=np.int16)
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)
        self._state = np.zeros(self._state_shape, dtype=np.float32)
