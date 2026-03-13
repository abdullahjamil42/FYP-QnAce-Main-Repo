"""
Q&Ace — Numpy Ring Buffer.

Pre-allocated circular buffer for 30 seconds of 16 kHz mono int16 audio.
Zero dynamic allocation during streaming — critical for latency.
"""

from __future__ import annotations

import numpy as np


class RingBuffer:
    """Fixed-capacity circular buffer backed by a pre-allocated numpy array."""

    def __init__(self, max_seconds: float = 30.0, sample_rate: int = 16_000):
        self.sample_rate = sample_rate
        self.capacity = int(max_seconds * sample_rate)
        self._buf = np.zeros(self.capacity, dtype=np.int16)
        self._write_pos = 0  # next write index (wraps)
        self._total_written = 0  # monotonic count of samples ever written

    # ── Write ──

    def write(self, samples: np.ndarray) -> None:
        """Append int16 samples. Overwrites oldest data when full."""
        n = len(samples)
        if n == 0:
            return
        if n >= self.capacity:
            # More data than buffer can hold — keep only the last `capacity` samples
            samples = samples[-self.capacity :]
            n = self.capacity

        end = self._write_pos + n
        if end <= self.capacity:
            self._buf[self._write_pos : end] = samples
        else:
            first = self.capacity - self._write_pos
            self._buf[self._write_pos :] = samples[:first]
            self._buf[: n - first] = samples[first:]

        self._write_pos = (self._write_pos + n) % self.capacity
        self._total_written += n

    # ── Read ──

    def read_last(self, num_samples: int) -> np.ndarray:
        """Return the most recent `num_samples` as a contiguous int16 array."""
        available = min(num_samples, self._total_written, self.capacity)
        if available == 0:
            return np.array([], dtype=np.int16)

        start = (self._write_pos - available) % self.capacity
        if start + available <= self.capacity:
            return self._buf[start : start + available].copy()
        else:
            first = self.capacity - start
            return np.concatenate([self._buf[start:], self._buf[: available - first]])

    def read_last_seconds(self, seconds: float) -> np.ndarray:
        """Convenience: read the last N seconds of audio."""
        return self.read_last(int(seconds * self.sample_rate))

    # ── State ──

    @property
    def duration_written(self) -> float:
        """Total seconds of audio ever written (including overwritten data)."""
        return self._total_written / self.sample_rate

    @property
    def available_seconds(self) -> float:
        """Seconds of audio currently readable."""
        return min(self._total_written, self.capacity) / self.sample_rate

    def clear(self) -> None:
        self._write_pos = 0
        self._total_written = 0
