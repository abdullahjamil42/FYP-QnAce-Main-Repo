from __future__ import annotations

import numpy as np
import pytest

from server.app.synthesis.tts import _float_audio_to_pcm_int16
import server.app.synthesis.tts as tts_module


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


@pytest.mark.asyncio
async def test_edge_stress_uses_native_rate_without_time_stretch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, str] = {}

    async def _fake_edge(text: str, voice: str, rate: str = "+0%") -> tts_module.TTSResult:
        calls["rate"] = rate
        return tts_module.TTSResult(
            np.array([0, 1024, -1024, 512, -512], dtype=np.int16),
            sample_rate=24_000,
            duration_s=0.05,
            inference_ms=1.0,
            engine_name="edge-tts",
        )

    def _fail_if_stretched(*_args, **_kwargs):
        raise AssertionError("time_stretch_audio should not be called for edge-tts")

    monkeypatch.setattr(tts_module, "_synthesize_edge", _fake_edge)
    monkeypatch.setattr(tts_module, "time_stretch_audio", _fail_if_stretched)

    engine = tts_module.TTSEngine(backend="tone")
    engine._engine_name = "edge-tts"

    res = await engine.synthesize("state your key result", stress_level="high")

    assert calls.get("rate") == "+12%"
    assert res.engine_name == "edge-tts"
    assert res.audio_pcm.dtype == np.int16
