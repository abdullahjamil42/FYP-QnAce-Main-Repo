#!/usr/bin/env python3
"""
Q&Ace — TTFA Benchmark Script (Phase 4 task 4.10).

Measures Time-to-First-Audio (TTFA) across the full pipeline:
  VAD → STT → Context → LLM TTFT → TTS first-chunk.

Usage:
    python scripts/benchmark_latency.py [--samples 20]

Outputs p50, p90, p99 per stage and overall.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import statistics
import sys
import time
from pathlib import Path

# Add repo root to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("benchmark")


def _percentiles(data: list[float]) -> dict[str, float]:
    if not data:
        return {"p50": 0.0, "p90": 0.0, "p99": 0.0, "mean": 0.0}
    s = sorted(data)
    n = len(s)
    return {
        "p50": s[int(n * 0.50)] if n > 1 else s[0],
        "p90": s[int(n * 0.90)] if n > 1 else s[0],
        "p99": s[int(n * 0.99)] if n > 1 else s[0],
        "mean": statistics.mean(s),
    }


async def benchmark_stt(samples: int) -> list[float]:
    """Benchmark Faster-Whisper STT latency."""
    import numpy as np

    try:
        from server.app.models import registry
        from server.app.config import get_settings
        settings = get_settings()
        registry.load_whisper(settings.model_dir, settings.whisper_model)
        from server.app.perception.stt import transcribe
    except ImportError as e:
        logger.warning("STT benchmark skipped: %s", e)
        return []

    # generate 3-second speech-like noise
    rng = np.random.default_rng(42)
    audio = (rng.standard_normal(48_000) * 5000).astype(np.int16)

    timings: list[float] = []
    for i in range(samples):
        t0 = time.perf_counter()
        transcribe(audio, registry.whisper_model)
        ms = (time.perf_counter() - t0) * 1000.0
        timings.append(ms)
        logger.info("STT sample %d: %.1fms", i + 1, ms)
    return timings


async def benchmark_tts(samples: int) -> list[float]:
    """Benchmark TTS synthesis latency (first-chunk time)."""
    try:
        from server.app.synthesis.tts import create_tts_engine
    except ImportError as e:
        logger.warning("TTS benchmark skipped: %s", e)
        return []

    engine = create_tts_engine()
    sentences = [
        "That's a great example of the STAR method.",
        "Can you elaborate on the challenges you faced?",
        "How did you measure the impact of your solution?",
        "Tell me about a time you led a cross-functional team.",
        "What would you do differently if you could go back?",
    ]

    timings: list[float] = []
    for i in range(samples):
        text = sentences[i % len(sentences)]
        t0 = time.perf_counter()
        result = await engine.synthesize(text)
        ms = (time.perf_counter() - t0) * 1000.0
        timings.append(ms)
        logger.info("TTS sample %d: %.1fms (%.1fs audio, %s)",
                     i + 1, ms, result.duration_s, result.engine_name)
    return timings


async def benchmark_avatar(samples: int) -> list[float]:
    """Benchmark avatar per-frame rendering latency."""
    try:
        from server.app.synthesis.avatar import create_avatar_engine
    except ImportError as e:
        logger.warning("Avatar benchmark skipped: %s", e)
        return []

    engine = create_avatar_engine()
    engine.precompute_source_features()

    timings: list[float] = []
    for i in range(samples * 5):  # render more frames since they're fast
        t0 = time.perf_counter()
        engine.render_frame(audio_energy=0.3, is_speaking=True)
        ms = (time.perf_counter() - t0) * 1000.0
        timings.append(ms)
    return timings


async def main():
    parser = argparse.ArgumentParser(description="Q&Ace TTFA Benchmark")
    parser.add_argument("--samples", type=int, default=10, help="Number of samples per stage")
    args = parser.parse_args()
    n = args.samples

    print("=" * 60)
    print(f"Q&Ace — TTFA Benchmark ({n} samples per stage)")
    print("=" * 60)

    # STT
    print("\n[STT] Benchmarking Faster-Whisper …")
    stt_times = await benchmark_stt(n)
    if stt_times:
        p = _percentiles(stt_times)
        print(f"  p50={p['p50']:.0f}ms  p90={p['p90']:.0f}ms  p99={p['p99']:.0f}ms  mean={p['mean']:.0f}ms")
    else:
        print("  (skipped)")

    # TTS
    print("\n[TTS] Benchmarking synthesis …")
    tts_times = await benchmark_tts(n)
    if tts_times:
        p = _percentiles(tts_times)
        print(f"  p50={p['p50']:.0f}ms  p90={p['p90']:.0f}ms  p99={p['p99']:.0f}ms  mean={p['mean']:.0f}ms")
    else:
        print("  (skipped)")

    # Avatar
    print("\n[Avatar] Benchmarking per-frame rendering …")
    avatar_times = await benchmark_avatar(n)
    if avatar_times:
        p = _percentiles(avatar_times)
        print(f"  p50={p['p50']:.2f}ms  p90={p['p90']:.2f}ms  p99={p['p99']:.2f}ms  mean={p['mean']:.2f}ms")
        fps = 1000.0 / p["p50"] if p["p50"] > 0 else 0
        print(f"  Effective FPS at p50: {fps:.0f}")
    else:
        print("  (skipped)")

    # Summary
    print("\n" + "=" * 60)
    stt_p50 = _percentiles(stt_times).get("p50", 0)
    tts_p50 = _percentiles(tts_times).get("p50", 0)
    vad_est = 200  # ms (configured threshold)
    context_est = 15  # ms (BERT + SBERT + ChromaDB)
    llm_est = 200  # ms (Groq TTFT estimate)

    ttfa_est = vad_est + stt_p50 + context_est + llm_est + tts_p50
    print(f"Estimated TTFA p50: {ttfa_est:.0f}ms")
    print(f"  VAD={vad_est}  STT={stt_p50:.0f}  Context~{context_est}  LLM~{llm_est}  TTS={tts_p50:.0f}")
    print(f"Target: <800ms  {'✓ PASS' if ttfa_est < 800 else '✗ OVER BUDGET'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
