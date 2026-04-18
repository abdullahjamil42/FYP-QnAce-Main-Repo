#!/usr/bin/env python3
"""Offline-only: generate hidden test cases (and optional benchmark stdin) via LLM, insert into Supabase.

NOT imported by the API server. Requires GROQ_API_KEY (or extend for other providers).

Usage:
  python scripts/seed_coding_hidden_offline.py --problem-id <uuid> --count 8

Or batch all problems missing hidden tests:
  python scripts/seed_coding_hidden_offline.py --all-missing --limit 5
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

import httpx
import requests

STRIP_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def strip_markdown_fences(text: str) -> str:
    t = text.strip()
    t = STRIP_FENCE.sub("", t).strip()
    return t


def supabase_headers() -> tuple[str, dict[str, str]]:
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    return url.rstrip("/"), headers


def groq_json(system: str, user: str) -> dict[str, Any] | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not set; skipping LLM generation", file=sys.stderr)
        return None
    payload = {
        "model": os.getenv("QACE_GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }
    try:
        r = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=120.0,
        )
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        text = strip_markdown_fences(text)
        return json.loads(text)
    except Exception as exc:
        print(f"LLM error: {exc}", file=sys.stderr)
        return None


def fetch_problem(url: str, headers: dict[str, str], pid: str) -> dict[str, Any] | None:
    r = requests.get(
        f"{url}/rest/v1/problems",
        headers=headers,
        params={"id": f"eq.{pid}", "select": "*"},
        timeout=60,
    )
    if r.status_code != 200 or not r.json():
        return None
    return r.json()[0]


def count_hidden(url: str, headers: dict[str, str], pid: str) -> int:
    r = requests.get(
        f"{url}/rest/v1/test_cases",
        headers=headers,
        params={"problem_id": f"eq.{pid}", "is_hidden": "eq.true", "select": "id"},
        timeout=60,
    )
    if r.status_code != 200:
        return 0
    return len(r.json())


def insert_tests(url: str, headers: dict[str, str], rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    r = requests.post(
        f"{url}/rest/v1/test_cases",
        headers={**headers, "Prefer": "return=minimal"},
        json=rows,
        timeout=120,
    )
    if r.status_code >= 300:
        raise RuntimeError(r.text[:500])


def patch_problem(url: str, headers: dict[str, str], pid: str, bench: dict[str, Any]) -> None:
    r = requests.patch(
        f"{url}/rest/v1/problems",
        headers=headers,
        params={"id": f"eq.{pid}"},
        json={"complexity_benchmark_stdin": bench},
        timeout=60,
    )
    if r.status_code >= 300:
        raise RuntimeError(r.text[:500])


def generate_for_problem(problem: dict[str, Any], count: int) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    system = (
        "You generate stdin/expected_output pairs for automated judging. "
        "Return ONLY valid JSON, no markdown."
    )
    user = json.dumps(
        {
            "task": "Create hidden test cases for stdin programs (one line or multi-line stdin as needed).",
            "problem_title": problem.get("title"),
            "description": problem.get("description", "")[:4000],
            "constraints": problem.get("constraints", ""),
            "count": count,
            "output_schema": {
                "test_cases": [{"stdin": "string with \\n where needed", "expected_output": "stdout to match exactly after trim"}],
                "complexity_benchmark_stdin": {
                    "n100": "stdin for n=100",
                    "n1000": "stdin for n=1000",
                    "n10000": "stdin for n=10000",
                },
            },
        }
    )
    data = groq_json(system, user)
    if not data:
        return [], None
    tests = data.get("test_cases") or []
    bench = data.get("complexity_benchmark_stdin")
    out = []
    for t in tests[:count]:
        if isinstance(t, dict) and "stdin" in t and "expected_output" in t:
            out.append(
                {
                    "stdin": str(t["stdin"]),
                    "expected_output": str(t["expected_output"]).strip(),
                }
            )
    bench_out = bench if isinstance(bench, dict) else None
    return out, bench_out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem-id", default=None)
    parser.add_argument("--count", type=int, default=6)
    parser.add_argument("--all-missing", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    url, headers = supabase_headers()

    if args.problem_id:
        p = fetch_problem(url, headers, args.problem_id)
        if not p:
            print("Problem not found", file=sys.stderr)
            return 1
        if count_hidden(url, headers, args.problem_id) >= args.count:
            print("Already has enough hidden tests; skipping")
            return 0
        tests, bench = generate_for_problem(p, args.count)
        rows = []
        for i, t in enumerate(tests):
            rows.append(
                {
                    "problem_id": args.problem_id,
                    "stdin": t["stdin"],
                    "expected_output": t["expected_output"],
                    "is_hidden": True,
                    "sort_order": 100 + i,
                }
            )
        insert_tests(url, headers, rows)
        if bench:
            patch_problem(url, headers, args.problem_id, bench)
        print(f"Inserted {len(rows)} hidden tests")
        return 0

    if args.all_missing:
        r = requests.get(
            f"{url}/rest/v1/problems",
            headers=headers,
            params={"select": "id,title,description,constraints", "limit": str(args.limit * 5)},
            timeout=60,
        )
        r.raise_for_status()
        problems = r.json()
        n = 0
        for p in problems:
            if n >= args.limit:
                break
            pid = p["id"]
            if count_hidden(url, headers, pid) > 0:
                continue
            tests, bench = generate_for_problem(p, args.count)
            if not tests:
                continue
            rows = [
                {
                    "problem_id": pid,
                    "stdin": t["stdin"],
                    "expected_output": t["expected_output"],
                    "is_hidden": True,
                    "sort_order": 100 + i,
                }
                for i, t in enumerate(tests)
            ]
            insert_tests(url, headers, rows)
            if bench:
                patch_problem(url, headers, pid, bench)
            n += 1
            print(f"Problem {pid}: {len(rows)} hidden tests")
        return 0

    print("Specify --problem-id or --all-missing", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
