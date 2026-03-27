from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests


def load_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("Manifest must be an array")
    return data


def normalize_question(topic_id: str, idx: int, raw: dict[str, Any]) -> dict[str, Any]:
    options = raw.get("options", [])
    if not isinstance(options, list):
        raise RuntimeError(f"Invalid options at {topic_id} #{idx}")
    if len(options) != 4:
        raise RuntimeError(f"Question must have 4 options at {topic_id} #{idx}")

    difficulty = str(raw.get("difficulty", "medium")).strip().lower()
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = "medium"

    return {
        "external_id": f"{topic_id}:{idx+1}",
        "topic_id": topic_id,
        "subtopic_title": str(raw.get("subtopic", "General")).strip() or "General",
        "difficulty": difficulty,
        "question": str(raw.get("question", "")).strip(),
        "options": options,
        "answer": str(raw.get("answer", "")).strip(),
        "explanation": str(raw.get("explanation", "")).strip(),
        "source": "bulk-generator",
    }


def load_topic_file(path: Path) -> tuple[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    topic_id = payload.get("topic_id")
    if not topic_id:
        topic_id = path.stem

    raw_questions = payload.get("questions", [])
    if not isinstance(raw_questions, list):
        raise RuntimeError(f"Invalid questions array in {path}")

    questions = [normalize_question(topic_id, i, q) for i, q in enumerate(raw_questions)]
    return topic_id, questions


def post_batch(
    url: str,
    headers: dict[str, str],
    rows: list[dict[str, Any]],
) -> None:
    endpoint = f"{url}/rest/v1/mcq_questions?on_conflict=external_id"
    batch_headers = {
        **headers,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    resp = requests.post(endpoint, headers=batch_headers, json=rows, timeout=120)
    if resp.status_code >= 300:
        raise RuntimeError(f"Supabase insert failed ({resp.status_code}): {resp.text[:400]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import generated MCQ JSON files into Supabase mcq_questions table.")
    parser.add_argument("--manifest", default="data/mcq_generated/manifest.json")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--topic-id", default=None)
    args = parser.parse_args()

    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    service_role = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url:
        raise RuntimeError("Missing SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL)")
    if not service_role:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")

    manifest = load_manifest(Path(args.manifest))
    if args.topic_id:
        manifest = [m for m in manifest if m.get("topic_id") == args.topic_id]
        if not manifest:
            raise RuntimeError(f"Topic not found in manifest: {args.topic_id}")

    headers = {
        "apikey": service_role,
        "Authorization": f"Bearer {service_role}",
    }

    total = 0
    for entry in manifest:
        topic_id = entry["topic_id"]
        file_path = Path(entry["file"])
        if not file_path.exists():
            raise RuntimeError(f"Missing generated file: {file_path}")

        parsed_topic_id, rows = load_topic_file(file_path)
        if parsed_topic_id != topic_id:
            print(f"Warning: topic_id mismatch {parsed_topic_id} vs manifest {topic_id}; using manifest value")
            for r in rows:
                r["topic_id"] = topic_id

        for i in range(0, len(rows), args.batch_size):
            post_batch(supabase_url, headers, rows[i : i + args.batch_size])

        print(f"Imported {len(rows)} rows for {topic_id}")
        total += len(rows)

    print(f"Done. Imported total rows: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
