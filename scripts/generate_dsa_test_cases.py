#!/usr/bin/env python3
"""
Offline script: Generate data/dsa_test_cases.json from dsa_final_a_plus.json.

For each problem in the bank, asks an LLM to generate:
  - 8 test cases (2 visible, 6 hidden) with stdin/expected_output matching the problem's python_code
  - complexity_benchmark_stdin entries for n=100, n=1000, n=10000

Output: data/dsa_test_cases.json  (dict keyed by string problem ID)

Usage:
    python scripts/generate_dsa_test_cases.py                   # all problems, resume
    python scripts/generate_dsa_test_cases.py --count 20        # first 20 problems
    python scripts/generate_dsa_test_cases.py --bank ./my_bank.json --output ./my_tests.json

Requirements:
    pip install httpx
    dsa_final_a_plus.json must exist at repo root (run generate_dsa_bank.py first)
    GROQ_API_KEY must be set (or AIRFORCE_API_URL for free fallback)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BANK = REPO_ROOT / "dsa_final_a_plus.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "dsa_test_cases.json"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
AIRFORCE_API_URL = "https://api.airforce/chat/completions"
AIRFORCE_MODEL = "llama-3.3-70b"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("dsa_tests_gen")


# ── LLM helpers ──────────────────────────────────────────────────────────────

class RateLimitError(Exception):
    pass


async def call_groq(client: httpx.AsyncClient, messages: list[dict], max_tokens: int = 2000) -> str | None:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        r = await client.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages, "temperature": 0.1, "max_tokens": max_tokens},
            timeout=90.0,
        )
        if r.status_code == 429:
            raise RateLimitError("429")
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except RateLimitError:
        raise
    except Exception as exc:
        logger.warning("Groq call failed: %s", exc)
        return None


async def call_airforce(client: httpx.AsyncClient, messages: list[dict], max_tokens: int = 2000) -> str | None:
    url = os.environ.get("AIRFORCE_API_URL", AIRFORCE_API_URL).rstrip("/") + "/chat/completions"
    try:
        r = await client.post(
            url,
            json={"model": AIRFORCE_MODEL, "messages": messages, "max_tokens": max_tokens},
            timeout=120.0,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("Airforce call failed: %s", exc)
        return None


async def call_llm(client: httpx.AsyncClient, messages: list[dict], max_tokens: int = 2000) -> str | None:
    try:
        result = await call_groq(client, messages, max_tokens)
        if result:
            return result
    except RateLimitError:
        logger.info("Rate limited — waiting 20s before retry")
        await asyncio.sleep(20)
        try:
            result = await call_groq(client, messages, max_tokens)
            if result:
                return result
        except RateLimitError:
            logger.info("Still rate limited — falling back to Airforce")
    return await call_airforce(client, messages, max_tokens)


def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        inner = lines[1:] if len(lines) > 1 else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()
    return text


# ── Test case generation ──────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a software engineer writing test cases for automated judging. "
    "The stdin format MUST exactly match what the provided python_code reads from sys.stdin. "
    "expected_output must exactly match (including whitespace) what the python_code prints. "
    "Return ONLY valid JSON, no markdown, no explanation."
)


def build_user_prompt(prob: dict[str, Any]) -> str:
    title = prob.get("title", "")
    desc = prob.get("problem_description") or prob.get("description") or ""
    python_code = (prob.get("python_code") or "")[:4000]
    examples = prob.get("examples") or []
    constraints = prob.get("constraints") or []

    examples_str = ""
    for ex in examples[:2]:
        if isinstance(ex, dict):
            examples_str += f"  Input: {ex.get('input', '')}\n  Output: {ex.get('output', '')}\n"

    constraints_str = "\n".join(f"  {c}" for c in constraints[:5])

    return f"""Problem: {title}

Description:
{desc[:2000]}

Examples:
{examples_str}

Constraints:
{constraints_str}

Reference Python code (shows exact stdin/stdout format):
```python
{python_code}
```

Generate test cases. Return JSON with exactly this structure:
{{
  "test_cases": [
    {{"stdin": "<exact stdin string>", "expected_output": "<exact stdout string>", "is_hidden": false}},
    {{"stdin": "...", "expected_output": "...", "is_hidden": false}},
    {{"stdin": "...", "expected_output": "...", "is_hidden": true}},
    {{"stdin": "...", "expected_output": "...", "is_hidden": true}},
    {{"stdin": "...", "expected_output": "...", "is_hidden": true}},
    {{"stdin": "...", "expected_output": "...", "is_hidden": true}},
    {{"stdin": "...", "expected_output": "...", "is_hidden": true}},
    {{"stdin": "...", "expected_output": "...", "is_hidden": true}}
  ],
  "complexity_benchmark_stdin": {{
    "n100": "<stdin with ~100 element input>",
    "n1000": "<stdin with ~1000 element input>",
    "n10000": "<stdin with ~10000 element input>"
  }}
}}

Rules:
- Exactly 8 test_cases: first 2 visible (is_hidden: false), last 6 hidden (is_hidden: true)
- Include edge cases among hidden tests: empty input, single element, duplicates, negatives, max constraints
- complexity_benchmark_stdin must match the stdin format the code reads — same format as test_cases stdin
- All strings must be valid JSON (escape newlines as \\n in the JSON string value)
"""


async def generate_test_cases(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    prob: dict[str, Any],
) -> dict[str, Any] | None:
    pid = str(prob["id"])
    async with sem:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(prob)},
        ]
        raw = await call_llm(client, messages, max_tokens=2500)
        if not raw:
            logger.warning("LLM returned nothing for problem %s (%s)", pid, prob.get("title"))
            return None
        try:
            data = json.loads(strip_fences(raw))
        except json.JSONDecodeError:
            logger.warning("JSON parse failed for problem %s (%s): %s", pid, prob.get("title"), raw[:300])
            return None

        # Validate structure
        test_cases = data.get("test_cases")
        bench = data.get("complexity_benchmark_stdin")

        if not isinstance(test_cases, list) or len(test_cases) == 0:
            logger.warning("No test_cases for problem %s (%s)", pid, prob.get("title"))
            return None

        # Ensure each test case has required fields
        clean_cases: list[dict] = []
        for tc in test_cases:
            if not isinstance(tc, dict):
                continue
            clean_cases.append({
                "stdin": str(tc.get("stdin", "")),
                "expected_output": str(tc.get("expected_output", "")),
                "is_hidden": bool(tc.get("is_hidden", False)),
            })

        if not clean_cases:
            return None

        # Validate benchmark
        clean_bench: dict[str, str] = {}
        if isinstance(bench, dict):
            for k in ("n100", "n1000", "n10000"):
                v = bench.get(k)
                if v is not None:
                    clean_bench[k] = str(v)

        return {
            "test_cases": clean_cases,
            "complexity_benchmark_stdin": clean_bench,
        }


# ── Main ──────────────────────────────────────────────────────────────────────

def save(output_path: Path, results: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved test cases for %d problems → %s", len(results), output_path)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate data/dsa_test_cases.json")
    parser.add_argument("--bank", default=str(DEFAULT_BANK), help="Path to dsa_final_a_plus.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON file path")
    parser.add_argument("--count", type=int, default=0, help="Max problems to process (0 = all)")
    parser.add_argument("--resume", action="store_true", default=True, help="Skip IDs already in output (default True)")
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.add_argument("--concurrency", type=int, default=5, help="Max parallel LLM calls")
    args = parser.parse_args()

    bank_path = Path(args.bank)
    if not bank_path.is_file():
        logger.error("Bank file not found: %s — run generate_dsa_bank.py first", bank_path)
        sys.exit(1)

    problems: list[dict] = json.loads(bank_path.read_text(encoding="utf-8"))
    logger.info("Loaded %d problems from bank", len(problems))

    output_path = Path(args.output)

    # Load existing output
    existing: dict[str, Any] = {}
    if args.resume and output_path.is_file():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            logger.info("Resuming: %d problems already have test cases", len(existing))
        except Exception as exc:
            logger.warning("Could not load existing output: %s", exc)

    # Apply --count and filter already done
    if args.count and args.count > 0:
        problems = problems[: args.count]

    to_process = [p for p in problems if str(p.get("id", "")) not in existing]
    logger.info("%d problems to process", len(to_process))

    if not to_process:
        logger.info("Nothing to do.")
        return

    sem = asyncio.Semaphore(args.concurrency)
    results: dict[str, Any] = dict(existing)
    completed = 0

    async with httpx.AsyncClient() as client:
        tasks = [generate_test_cases(client, sem, prob) for prob in to_process]
        prob_ids = [str(p.get("id", i)) for i, p in enumerate(to_process)]

        for i, coro in enumerate(asyncio.as_completed(tasks)):
            tc_data = await coro
            pid = prob_ids[i]
            if tc_data is not None:
                results[pid] = tc_data
            completed += 1
            if completed % 25 == 0:
                logger.info("Progress: %d / %d", completed, len(tasks))
                save(output_path, results)

    save(output_path, results)
    logger.info("Done. Test cases for %d / %d problems saved.", len(results), len(problems))


if __name__ == "__main__":
    asyncio.run(main())
