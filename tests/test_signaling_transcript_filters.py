from __future__ import annotations

import numpy as np

from server.app.webrtc.signaling import _should_filter_silence_transcript


def test_filters_common_silence_hallucination_phrase() -> None:
    silence = np.zeros(16_000, dtype=np.int16)
    assert _should_filter_silence_transcript("thank you", silence) is True


def test_keeps_meaningful_transcript_with_clear_voice_energy() -> None:
    sr = 16_000
    t = np.linspace(0, 1.5, int(sr * 1.5), endpoint=False)
    voiced = (np.sin(2 * np.pi * 180 * t) * 9000).astype(np.int16)

    assert (
        _should_filter_silence_transcript(
            "I designed a cache invalidation strategy for our API.",
            voiced,
        )
        is False
    )


def test_filters_very_low_energy_short_utterance() -> None:
    rng = np.random.default_rng(0)
    low_energy_noise = rng.integers(-80, 80, size=16_000, dtype=np.int16)

    assert _should_filter_silence_transcript("yes", low_energy_noise) is True
