from __future__ import annotations

import numpy as np

from server.app.synthesis.tts import _float_audio_to_pcm_int16


def test_float_to_pcm_downmixes_stereo_channel_first() -> None:
    stereo = np.array(
        [
            [0.5, -0.5, 0.25, -0.25],
            [0.25, -0.25, 0.5, -0.5],
        ],
        dtype=np.float32,
    )

    pcm = _float_audio_to_pcm_int16(stereo)
    assert pcm.dtype == np.int16
    assert pcm.ndim == 1
    assert len(pcm) == 4
    assert int(np.max(np.abs(pcm))) <= 32767


def test_float_to_pcm_sanitizes_nan_and_inf_values() -> None:
    unstable = np.array([0.1, np.nan, np.inf, -np.inf, -0.2], dtype=np.float32)

    pcm = _float_audio_to_pcm_int16(unstable)
    assert pcm.dtype == np.int16
    assert pcm.tolist()[1] == 0
    assert int(np.max(np.abs(pcm))) <= 32767
