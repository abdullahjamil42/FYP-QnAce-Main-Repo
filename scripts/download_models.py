#!/usr/bin/env python3
"""
Q&Ace — Model Download Script.

Downloads all required model weights to the ./models directory.
Idempotent: skips models that already exist locally.

Usage:
    python scripts/download_models.py
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# Repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def download_silero_vad():
    """Download Silero VAD v5 ONNX model."""
    dest = MODELS_DIR / "silero-vad"
    onnx_path = dest / "silero_vad.onnx"
    if onnx_path.exists():
        print(f"  ✓ Silero VAD already at {onnx_path}")
        return

    ensure_dir(dest)
    print("  ↓ Downloading Silero VAD v5 ONNX …")
    try:
        import requests

        url = "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(onnx_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  ✓ Silero VAD saved to {onnx_path}")
    except Exception as exc:
        print(f"  ✗ Silero VAD download failed: {exc}")


def download_whisper():
    """Download Faster-Whisper distil-large-v3 via huggingface_hub."""
    marker = MODELS_DIR / "whisper-distil-large-v3" / ".downloaded"
    if marker.exists():
        print(f"  ✓ Whisper distil-large-v3 already downloaded")
        return

    print("  ↓ Downloading Faster-Whisper distil-large-v3 (this may take a while) …")
    try:
        from faster_whisper import WhisperModel

        _ = WhisperModel(
            "distil-large-v3",
            device="cpu",
            compute_type="int8",
            download_root=str(MODELS_DIR),
        )
        ensure_dir(marker.parent)
        marker.touch()
        print("  ✓ Whisper distil-large-v3 downloaded")
    except ImportError:
        print("  ✗ faster-whisper not installed — skipping Whisper download")
    except Exception as exc:
        print(f"  ✗ Whisper download failed: {exc}")


def download_qwen_tts_assets():
    """Bootstrap Qwen3-TTS 0.6B and tokenizer into models/qwen3-tts."""
    dest = MODELS_DIR / "qwen3-tts"
    model_dir = dest / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
    tokenizer_dir = dest / "Qwen3-TTS-Tokenizer-12Hz"
    if model_dir.exists() and tokenizer_dir.exists():
        print("  ✓ Qwen3-TTS 0.6B assets already bootstrapped")
        return

    ensure_dir(dest)
    print("  ℹ Qwen3-TTS 0.6B runtime is enabled in config.")
    print("  Download manually if startup-time download is undesirable:")
    print("    huggingface-cli download Qwen/Qwen3-TTS-Tokenizer-12Hz --local-dir ./models/qwen3-tts/Qwen3-TTS-Tokenizer-12Hz")
    print("    huggingface-cli download Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice --local-dir ./models/qwen3-tts/Qwen3-TTS-12Hz-0.6B-CustomVoice")


def main():
    print("=" * 60)
    print("Q&Ace — Model Download")
    print("=" * 60)
    ensure_dir(MODELS_DIR)

    print("\n[1/4] Silero VAD")
    download_silero_vad()

    print("\n[2/4] Faster-Whisper distil-large-v3")
    download_whisper()

    print("\n[3/4] TTS (Qwen3-TTS 0.6B)")
    download_qwen_tts_assets()

    print("\n[4/4] Avatar")
    avatar_dir = MODELS_DIR / "avatar"
    ensure_dir(avatar_dir)
    interviewer_png = avatar_dir / "interviewer.png"
    if interviewer_png.exists():
        print(f"  ✓ Avatar image already at {interviewer_png}")
    else:
        print(f"  ℹ No avatar image found. Using procedurally generated fallback.")
        print(f"  To customize, place a 512×512 PNG at: {interviewer_png}")
    print("  (Future: LivePortrait + MuseTalk weights would go to models/avatar/)")

    print("\n" + "=" * 60)
    print("Done. Model directory:", MODELS_DIR)
    print("=" * 60)


if __name__ == "__main__":
    main()
