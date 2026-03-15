from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification  # type: ignore
import uvicorn
import numpy as np

app = FastAPI(title="Text Quality Service (BERT)", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model paths (local fine-tuned model directory)
MODEL_DIR = Path(__file__).resolve().parents[1]

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

try:
    # Prefer local model first
    model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR))
    model.to(device)
    model.eval()

    # Try a local tokenizer; if not present (e.g., missing vocab.txt), fall back to a base tokenizer
    try:
        tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    except Exception:
        tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
except Exception as e:
    raise RuntimeError(
        "Failed to load BERT model from {}: {}. "
        "If this persists, ensure the directory contains a compatible tokenizer (e.g., vocab.txt, tokenizer.json). "
        "Otherwise the service will fall back to 'bert-base-uncased' tokenizer.".format(MODEL_DIR, e)
    )

# Obtain label mapping from config if present
if hasattr(model.config, "id2label") and model.config.id2label:
    # Normalize keys to int in case they are strings in config.json
    id2label = {int(k): v for k, v in model.config.id2label.items()}
else:
    id2label = {0: "LABEL_0"}


class AnalyzeTextRequest(BaseModel):
    text: str
    top_k: int | None = 3


class TopKItem(BaseModel):
    label: str
    prob: float


class AnalyzeTextResponse(BaseModel):
    predicted_label: str
    probabilities: Dict[str, float]
    top_k: List[TopKItem]


@app.get("/health")
def health():
    return {"status": "ok", "device": str(device)}


@app.post("/analyze/text", response_model=AnalyzeTextResponse)
def analyze_text(payload: AnalyzeTextRequest):
    if not payload.text or not payload.text.strip():
        return AnalyzeTextResponse(predicted_label="", probabilities={}, top_k=[])

    enc = tokenizer(
        payload.text,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )
    enc = {k: v.to(device) for k, v in enc.items()}

    with torch.no_grad():
        outputs = model(**enc)
        logits = outputs.logits.detach().cpu().numpy()[0]
        probs = (np.exp(logits) / np.sum(np.exp(logits))).astype(float)

    # Map to label names
    probs_dict = {id2label.get(i, str(i)): float(probs[i]) for i in range(len(probs))}
    top_idx = int(np.argmax(probs))

    # Top-k list
    k = min(payload.top_k or 3, len(probs))
    top_k_pairs = sorted(probs_dict.items(), key=lambda x: x[1], reverse=True)[:k]
    top_k = [{"label": lbl, "prob": float(p)} for lbl, p in top_k_pairs]

    return AnalyzeTextResponse(
        predicted_label=id2label.get(top_idx, str(top_idx)),
        probabilities=probs_dict,
        top_k=top_k,
    )


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8002, reload=True)
