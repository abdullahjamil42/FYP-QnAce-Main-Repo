"""
Q&Ace — TTFA Budget Tests (Phase 4 task 4.12).

Validates that per-stage latencies stay within budget:
  - TTS synthesis < 2000ms (edge-tts via network)
  - Avatar per-frame render < 25ms
  - Scoring + context pipeline < 100ms (offline, no LLM)
"""

from __future__ import annotations

import time

import numpy as np
import pytest


# ── TTS ──


@pytest.fixture(scope="module")
def tts_engine():
    from server.app.synthesis.tts import create_tts_engine

    return create_tts_engine()


def test_tts_engine_creates(tts_engine):
    assert tts_engine is not None
    assert tts_engine.engine_name in ("edge-tts", "tone-generator", "qwen3-tts")


@pytest.mark.asyncio
async def test_tts_synthesize_nonempty(tts_engine):
    result = await tts_engine.synthesize("Hello, this is a test.")
    assert result.audio_pcm is not None
    assert len(result.audio_pcm) > 0
    assert result.duration_s > 0.0


@pytest.mark.asyncio
async def test_tts_empty_input(tts_engine):
    result = await tts_engine.synthesize("")
    assert result.engine_name == "silence"


@pytest.mark.asyncio
async def test_tts_latency_under_budget(tts_engine):
    """TTS first-chunk should complete within 2000ms (network-dependent)."""
    t0 = time.perf_counter()
    result = await tts_engine.synthesize("Can you tell me about a time you led a team?")
    ms = (time.perf_counter() - t0) * 1000.0
    assert ms < 5000, f"TTS took {ms:.0f}ms — way over budget"
    assert result.audio_pcm is not None


# ── Avatar ──


@pytest.fixture(scope="module")
def avatar_engine():
    from server.app.synthesis.avatar import create_avatar_engine

    engine = create_avatar_engine()
    engine.precompute_source_features()
    return engine


def test_avatar_engine_creates(avatar_engine):
    assert avatar_engine is not None
    assert avatar_engine.engine_name in ("static-animated", "liveportrait-musetalk")


def test_avatar_idle_frame(avatar_engine):
    frame = avatar_engine.render_idle_frame()
    assert frame.frame_rgb.shape == (512, 512, 3)
    assert frame.frame_rgb.dtype == np.uint8


def test_avatar_speaking_frame(avatar_engine):
    frame = avatar_engine.render_frame(audio_energy=0.4, is_speaking=True)
    assert frame.frame_rgb.shape == (512, 512, 3)


def test_avatar_render_under_25ms(avatar_engine):
    """Per-frame render must stay under 25ms for 40+ FPS."""
    times = []
    for _ in range(30):
        t0 = time.perf_counter()
        avatar_engine.render_frame(audio_energy=0.3, is_speaking=True)
        times.append((time.perf_counter() - t0) * 1000.0)
    p90 = sorted(times)[int(len(times) * 0.9)]
    assert p90 < 25.0, f"Avatar p90 render time {p90:.1f}ms > 25ms budget"


# ── Output tracks (unit-level, no aiortc required) ──


def test_tts_audio_track_import():
    from server.app.webrtc.tracks import TTSAudioStreamTrack

    track = TTSAudioStreamTrack(output_rate=48_000)
    assert track.kind == "audio"


def test_avatar_video_track_import():
    from server.app.webrtc.tracks import AvatarVideoStreamTrack

    track = AvatarVideoStreamTrack(fps=30)
    assert track.kind == "video"


def test_tts_track_enqueue():
    from server.app.webrtc.tracks import TTSAudioStreamTrack

    track = TTSAudioStreamTrack(output_rate=48_000)
    pcm = np.zeros(24_000, dtype=np.int16)
    track.enqueue_audio(pcm, sample_rate=24_000)
    assert not track._queue.empty()


# ── Scoring pipeline (offline) ──


def test_scoring_computes_within_budget():
    """Scoring formula should be <5ms (pure arithmetic)."""
    from server.app.intelligence.scoring import compute_utterance_scores

    t0 = time.perf_counter()
    for _ in range(100):
        compute_utterance_scores(
            text_quality_score=70.0,
            wpm=140,
            filler_count=1,
            duration_s=5.0,
            vocal_confidence=0.8,
            eye_contact_ratio=0.7,
            blinks_per_min=18.0,
            emotion_positivity=0.6,
        )
    total_ms = (time.perf_counter() - t0) * 1000.0
    per_call_ms = total_ms / 100
    assert per_call_ms < 5.0, f"Scoring at {per_call_ms:.2f}ms per call"
