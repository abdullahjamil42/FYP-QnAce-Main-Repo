"""
Q&Ace — Test fixtures (pytest conftest).
"""

from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture
def sample_audio_silence():
    """2 seconds of silence at 16 kHz (all zeros)."""
    return np.zeros(32_000, dtype=np.int16)


@pytest.fixture
def sample_audio_speech():
    """2 seconds of synthetic 'speech' — 440 Hz sine wave at 16 kHz."""
    sr = 16_000
    t = np.linspace(0, 2.0, sr * 2, endpoint=False)
    tone = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    return tone


@pytest.fixture
def sample_audio_mixed():
    """1s speech + 0.5s silence + 1s speech at 16 kHz."""
    sr = 16_000
    t1 = np.linspace(0, 1.0, sr, endpoint=False)
    speech1 = (np.sin(2 * np.pi * 440 * t1) * 16000).astype(np.int16)
    silence = np.zeros(sr // 2, dtype=np.int16)
    t2 = np.linspace(0, 1.0, sr, endpoint=False)
    speech2 = (np.sin(2 * np.pi * 440 * t2) * 16000).astype(np.int16)
    return np.concatenate([speech1, silence, speech2])
