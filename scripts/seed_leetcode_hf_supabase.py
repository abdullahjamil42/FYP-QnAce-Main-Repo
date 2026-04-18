#!/usr/bin/env python3
"""Load LeetCode-style problems into Supabase `problems` + `test_cases`.

Usage:
  # From bundled sample (no HF):
  python scripts/seed_leetcode_hf_supabase.py --file data/coding_sample_problems.json

  # From Hugging Face (requires: pip install datasets pyarrow):
  python scripts/seed_leetcode_hf_supabase.py --hf neenza/leetcode-problems --limit 50

Env: SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL), SUPABASE_SERVICE_ROLE_KEY.
Loads .env, client/.env.local, client/_env.local (later overrides).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for rel in (".env", "client/.env.local", "client/_env.local", "server/.env"):
        p = REPO_ROOT / rel
        if p.is_file():
            load_dotenv(p, override=True)


_load_dotenv()


def supabase_headers() -> tuple[str, dict[str, str]]:
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    return url.rstrip("/"), headers


def post_problems(url: str, headers: dict[str, str], rows: list[dict[str, Any]]) -> None:
    endpoint = f"{url}/rest/v1/problems?on_conflict=external_slug"
    h = {**headers, "Prefer": "resolution=merge-duplicates,return=representation"}
    resp = requests.post(endpoint, headers=h, json=rows, timeout=120)
    if resp.status_code >= 300:
        raise RuntimeError(f"problems insert failed ({resp.status_code}): {resp.text[:500]}")
    return resp.json() if resp.text else []


def post_tests(url: str, headers: dict[str, str], rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    endpoint = f"{url}/rest/v1/test_cases"
    h = {**headers, "Prefer": "return=minimal"}
    resp = requests.post(endpoint, headers=h, json=rows, timeout=120)
    if resp.status_code >= 300:
        raise RuntimeError(f"test_cases insert failed ({resp.status_code}): {resp.text[:500]}")


def load_json_file(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    problems = data.get("problems", data)
    if not isinstance(problems, list):
        raise RuntimeError("JSON must have a 'problems' array or be an array")
    return problems


def normalize_hf_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map HF dataset row to our problem shape (best-effort)."""
    title = str(row.get("title") or row.get("Title") or "Untitled")
    slug = str(row.get("slug") or row.get("id") or title.lower().replace(" ", "-"))[:200]
    desc = str(row.get("description") or row.get("problem_statement") or row.get("content") or "")
    diff = str(row.get("difficulty") or "medium").lower()
    if diff not in ("easy", "medium", "hard"):
        diff = "medium"
    topics = row.get("topics") or row.get("topicTags") or []
    if isinstance(topics, str):
        topics = [topics]
    if isinstance(topics, list) and topics and isinstance(topics[0], dict):
        topics = [t.get("name", "") for t in topics]
    examples = row.get("examples") or row.get("sample_test_cases") or []
    if isinstance(examples, str):
        try:
            examples = json.loads(examples)
        except json.JSONDecodeError:
            examples = []
    constraints = str(row.get("constraints") or "")
    hints = row.get("hints") or []
    if isinstance(hints, str):
        hints = [hints]
    bench = row.get("complexity_benchmark_stdin")
    if bench is not None and not isinstance(bench, dict):
        bench = None
    tests_raw = row.get("test_cases") or row.get("public_test_cases") or []
    test_cases: list[dict[str, Any]] = []
    if isinstance(tests_raw, list):
        for i, t in enumerate(tests_raw):
            if isinstance(t, dict):
                test_cases.append(
                    {
                        "stdin": str(t.get("stdin", t.get("input", ""))),
                        "expected_output": str(t.get("expected_output", t.get("output", ""))).strip(),
                        "is_hidden": bool(t.get("is_hidden", False)),
                        "sort_order": i,
                    }
                )
    if not test_cases:
        test_cases = [
            {"stdin": "1\n", "expected_output": "1", "is_hidden": False, "sort_order": 0},
        ]
    return {
        "external_slug": slug,
        "title": title[:500],
        "difficulty": diff,
        "topics": topics if isinstance(topics, list) else [],
        "description": desc,
        "examples": examples if isinstance(examples, list) else [],
        "constraints": constraints,
        "hints": hints if isinstance(hints, list) else [],
        "complexity_benchmark_stdin": bench,
        "test_cases": test_cases,
    }


def load_hf(hf_id: str, limit: int) -> list[dict[str, Any]]:
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError as e:
        raise RuntimeError("pip install datasets pyarrow for --hf") from e

    ds = load_dataset(hf_id, split="train", streaming=True)
    out: list[dict[str, Any]] = []
    for i, row in enumerate(ds):
        if i >= limit:
            break
        if not isinstance(row, dict):
            continue
        out.append(normalize_hf_row(row))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, help="JSON file with problems[]")
    parser.add_argument("--hf", default=None, help="HuggingFace dataset id")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    if args.file:
        problems = load_json_file(REPO_ROOT / args.file if not args.file.is_absolute() else args.file)
    elif args.hf:
        problems = load_hf(args.hf, args.limit)
    else:
        default_path = REPO_ROOT / "data" / "coding_sample_problems.json"
        print(f"No --file or --hf; using {default_path}", file=sys.stderr)
        problems = load_json_file(default_path)

    url, headers = supabase_headers()

    for p in problems:
        if "test_cases" not in p:
            p["test_cases"] = []
        row = {
            "external_slug": p.get("external_slug") or p["title"].lower().replace(" ", "-")[:200],
            "title": p["title"],
            "difficulty": p.get("difficulty", "medium"),
            "topics": p.get("topics", []),
            "description": p.get("description", ""),
            "examples": p.get("examples", []),
            "constraints": p.get("constraints", ""),
            "hints": p.get("hints", []),
            "complexity_benchmark_stdin": p.get("complexity_benchmark_stdin"),
        }
        inserted = post_problems(url, headers, [row])
        pid = None
        if isinstance(inserted, list) and inserted:
            pid = inserted[0].get("id")
        if not pid:
            sel = requests.get(
                f"{url}/rest/v1/problems",
                headers=headers,
                params={"external_slug": f"eq.{row['external_slug']}", "select": "id"},
                timeout=60,
            )
            if sel.status_code == 200 and sel.json():
                pid = sel.json()[0]["id"]
        if not pid:
            print(f"Could not resolve id for {row['external_slug']}", file=sys.stderr)
            continue
        tests = []
        for t in p.get("test_cases", []):
            tests.append(
                {
                    "problem_id": pid,
                    "stdin": t.get("stdin", ""),
                    "expected_output": str(t.get("expected_output", "")).strip(),
                    "is_hidden": bool(t.get("is_hidden", False)),
                    "sort_order": t.get("sort_order", len(tests)),
                }
            )
        post_tests(url, headers, tests)
        print(f"Seeded {row['external_slug']} ({len(tests)} tests)")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
