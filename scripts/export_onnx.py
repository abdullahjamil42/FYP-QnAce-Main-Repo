#!/usr/bin/env python3
"""
Q&Ace — ONNX / Model Bootstrap Script.

Creates the missing runtime assets required by the current QACE_Final repo:
  1. Silero VAD ONNX            -> models/silero-vad/silero_vad.onnx
  2. Face emotion ONNX          -> models/face-emotion/efficientnet_b2.onnx
  3. BERT text-quality ONNX     -> models/text-quality/bert_quality.onnx

It can reuse local assets from the older QnAce repo when available.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"

SILERO_ONNX = MODELS_DIR / "silero-vad" / "silero_vad.onnx"
FACE_ONNX = MODELS_DIR / "face-emotion" / "efficientnet_b2.onnx"
BERT_ONNX = MODELS_DIR / "text-quality" / "bert_quality.onnx"

OLD_QNACE_ROOT = Path(r"C:\22i-2451\QAce\FYP-QnAce-Main-Repo")
OLD_BERT_DIR = OLD_QNACE_ROOT / "BERT_Model"

FACE_HF_REPO = "abdullahjamil42/QnAce-Face-Model"
FACE_HF_URL = f"https://huggingface.co/{FACE_HF_REPO}/resolve/main/model.safetensors"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def export_silero() -> None:
    if SILERO_ONNX.exists():
        print(f"✓ Silero already present: {SILERO_ONNX}")
        return

    ensure_dir(SILERO_ONNX.parent)
    print("↓ Downloading Silero VAD ONNX …")

    import requests

    url = "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    with open(SILERO_ONNX, "wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)

    print(f"✓ Silero saved: {SILERO_ONNX}")


def export_face_onnx() -> None:
    if FACE_ONNX.exists():
        print(f"✓ Face ONNX already present: {FACE_ONNX}")
        return

    print("↓ Exporting face emotion model to ONNX …")
    ensure_dir(FACE_ONNX.parent)

    import requests
    import timm
    import torch
    import torch.nn as nn
    from safetensors import safe_open

    tmp_path = FACE_ONNX.parent / "face_model.safetensors"
    if not tmp_path.exists():
        response = requests.get(FACE_HF_URL, timeout=180)
        response.raise_for_status()
        tmp_path.write_bytes(response.content)

    model = timm.create_model("efficientnet_b2.ra_in1k", pretrained=False)
    in_features = model.classifier.in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(in_features, 512),
        nn.ReLU(inplace=True),
        nn.Dropout(p=0.3),
        nn.Linear(512, 7),
    )

    state_dict: dict[str, torch.Tensor] = {}
    with safe_open(str(tmp_path), framework="pt", device="cpu") as handle:
        for key in handle.keys():
            mapped_key = key[9:] if key.startswith("backbone.") else key
            state_dict[mapped_key] = handle.get_tensor(key)

    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    if missing:
        print(f"  ! Face export missing keys: {len(missing)}")
    if unexpected:
        print(f"  ! Face export unexpected keys: {len(unexpected)}")

    model.eval()
    dummy = torch.randn(1, 3, 224, 224, dtype=torch.float32)
    torch.onnx.export(
        model,
        dummy,
        str(FACE_ONNX),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=18,
    )
    print(f"✓ Face ONNX exported: {FACE_ONNX}")


def export_bert_onnx() -> None:
    if BERT_ONNX.exists():
        print(f"✓ BERT ONNX already present: {BERT_ONNX}")
        return

    if not OLD_BERT_DIR.exists():
        raise FileNotFoundError(f"Local BERT model folder not found: {OLD_BERT_DIR}")

    print("↓ Exporting BERT text-quality model to ONNX …")
    ensure_dir(BERT_ONNX.parent)

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    model = AutoModelForSequenceClassification.from_pretrained(str(OLD_BERT_DIR))
    tokenizer = AutoTokenizer.from_pretrained(str(OLD_BERT_DIR))
    model.eval()

    sample = tokenizer(
        "I handled a difficult project by breaking it into milestones and tracking outcomes.",
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=128,
    )

    torch.onnx.export(
        model,
        (sample["input_ids"], sample["attention_mask"], sample.get("token_type_ids")),
        str(BERT_ONNX),
        input_names=["input_ids", "attention_mask", "token_type_ids"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "sequence"},
            "attention_mask": {0: "batch", 1: "sequence"},
            "token_type_ids": {0: "batch", 1: "sequence"},
            "logits": {0: "batch"},
        },
        opset_version=18,
    )

    # Keep tokenizer/config files near the ONNX model for optional direct use.
    for name in ["config.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"]:
        src = OLD_BERT_DIR / name
        if src.exists():
            shutil.copy2(src, BERT_ONNX.parent / name)

    print(f"✓ BERT ONNX exported: {BERT_ONNX}")


def main() -> int:
    ensure_dir(MODELS_DIR)
    try:
        export_silero()
        export_face_onnx()
        export_bert_onnx()
    except Exception as exc:  # pragma: no cover - bootstrap utility
        print(f"✗ Bootstrap failed: {exc}")
        return 1

    print("\nAll runtime assets are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())