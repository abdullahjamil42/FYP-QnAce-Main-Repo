#!/usr/bin/env python3
"""
Offline script: Build dsa_final_a_plus.json from the neenza/leetcode-problems dataset.

Downloads the neenza JSON (or reads a local file), enriches each problem with LLM-generated
optimal_approach, python_code, time_complexity, space_complexity, then writes the output file.

Usage:
    python scripts/generate_dsa_bank.py                          # all 2913, neenza URL
    python scripts/generate_dsa_bank.py --count 20 --resume     # 20 problems, skip already done
    python scripts/generate_dsa_bank.py --source /path/to/problems.json --output out.json

Requirements:
    pip install httpx
    GROQ_API_KEY must be set (or AIRFORCE_API_URL for free fallback)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
NEENZA_URL = "https://raw.githubusercontent.com/neenza/leetcode-problems/master/merged_problems.json"
NEENZA_LOCAL = REPO_ROOT / "data" / "merged_problems.json"
DEFAULT_OUTPUT = REPO_ROOT / "dsa_final_a_plus.json"

# Load .env from repo root so GROQ_API_KEY etc. are available without pre-exporting
_env_file = REPO_ROOT / ".env"
if _env_file.is_file():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Global Groq cooldown — if time.monotonic() < this, skip Groq and go straight to Airforce
_groq_available_at: float = 0.0

# Airforce free fallback — base URL only (path appended in call_airforce)
AIRFORCE_BASE_URL = "https://api.airforce"
AIRFORCE_MODEL = "llama-4-scout"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("dsa_bank_gen")


# ── LLM call ─────────────────────────────────────────────────────────────────

async def call_groq(client: httpx.AsyncClient, messages: list[dict], max_tokens: int = 4096, json_mode: bool = True) -> str | None:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        body: dict = {
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        r = await client.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=60.0,
        )
        if r.status_code == 429:
            retry_after = float(r.headers.get("retry-after", 0))
            raise RateLimitError("429", retry_after=retry_after)
        if r.status_code == 400:
            logger.warning("Groq 400 error: %s", r.text[:300])
            return None
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except RateLimitError:
        raise
    except Exception as exc:
        logger.warning("Groq call failed: %s", exc)
        return None


async def call_airforce(client: httpx.AsyncClient, messages: list[dict], max_tokens: int = 2048) -> str | None:
    # Try /v1/chat/completions first, fall back to /chat/completions
    base = os.environ.get("AIRFORCE_API_URL", AIRFORCE_BASE_URL).rstrip("/")
    for path in ("/v1/chat/completions", "/chat/completions"):
        url = base + path
        for attempt in range(3):
            try:
                r = await client.post(
                    url,
                    json={"model": AIRFORCE_MODEL, "messages": messages, "max_tokens": max_tokens},
                    timeout=90.0,
                )
                if r.status_code in (404, 405):
                    break  # this path doesn't work, try next
                if r.status_code == 429:
                    wait = float(r.headers.get("retry-after", 5 * (attempt + 1)))
                    wait = min(wait, 30.0)
                    logger.info("Airforce 429 (attempt %d) — waiting %.0fs", attempt + 1, wait)
                    await asyncio.sleep(wait)
                    continue
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                # Airforce returns 200 with an error message when model is unsupported
                if "does not exist" in content or "discord.gg" in content:
                    logger.warning("Airforce model error: %s", content[:120])
                    return None
                # Strip proxy advertisement footer injected by some Airforce nodes
                if "\n\nNeed proxies" in content:
                    content = content[:content.index("\n\nNeed proxies")]
                return content
            except Exception as exc:
                logger.warning("Airforce call failed (%s): %s", url, exc)
                break  # non-429 exception — try next path
    return None


class RateLimitError(Exception):
    def __init__(self, msg: str, retry_after: float = 0.0):
        super().__init__(msg)
        self.retry_after = retry_after


async def call_llm(client: httpx.AsyncClient, messages: list[dict], max_tokens: int = 4096) -> str | None:
    """Try Groq once (if not in cooldown), fall back to Airforce immediately."""
    global _groq_available_at
    now = time.monotonic()
    if now >= _groq_available_at:
        try:
            result = await call_groq(client, messages, max_tokens, json_mode=True)
            if result:
                return result
            result = await call_groq(client, messages, max_tokens, json_mode=False)
            if result:
                return result
        except RateLimitError as e:
            # On 429, put Groq in cooldown for the indicated duration (min 60s, max 3600s)
            cooldown = e.retry_after if e.retry_after > 0 else 60.0
            cooldown = max(60.0, min(cooldown, 3600.0))
            _groq_available_at = time.monotonic() + cooldown
            logger.info("Groq rate-limited — cooling down for %.0fs (Airforce will handle in meantime)", cooldown)
    else:
        remaining = _groq_available_at - now
        logger.debug("Groq in cooldown for %.0fs more — going straight to Airforce", remaining)
    return await call_airforce(client, messages, max_tokens)


def strip_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        inner = lines[1:] if len(lines) > 1 else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()
    return text


# ── Problem enrichment ────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a senior software engineer. "
    "Return ONLY a single valid JSON object — no markdown, no commentary, no extra keys. "
    "The JSON must have exactly these 4 keys: "
    "optimal_approach (1-2 short sentences), "
    "python_code (complete Python 3 class + __main__ block), "
    "time_complexity (e.g. O(n)), "
    "space_complexity (e.g. O(1))."
)


def build_user_prompt(prob: dict[str, Any]) -> str:
    title = prob.get("title", "")
    desc = prob.get("description", "")
    examples_raw = prob.get("examples", [])
    constraints_raw = prob.get("constraints", [])

    examples_str = ""
    if examples_raw:
        parts = []
        for ex in examples_raw[:3]:
            if isinstance(ex, dict):
                # neenza schema: example_text is a pre-formatted string
                parts.append(ex.get("example_text") or f"Input: {ex.get('input', '')}\nOutput: {ex.get('output', '')}")
            else:
                parts.append(str(ex))
        examples_str = "\n".join(parts)

    constraints_str = "\n".join(str(c) for c in (constraints_raw or [])[:5])

    return f"""Problem: {title}

Description:
{desc[:1500]}

Examples:
{examples_str}

Constraints:
{constraints_str}

Respond with JSON only:
- "optimal_approach": 1-2 sentences max describing the key algorithm/data structure
- "python_code": complete Python 3 with `class Solution` + `if __name__ == '__main__':` block reading from stdin
- "time_complexity": e.g. "O(n)"
- "space_complexity": e.g. "O(1)"
"""


async def enrich_problem(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    prob: dict[str, Any],
    idx: int,
) -> dict[str, Any] | None:
    """Enrich one neenza problem entry with LLM-generated fields."""
    async with sem:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(prob)},
        ]
        raw = await call_llm(client, messages, max_tokens=4096)
        if not raw:
            logger.warning("LLM returned nothing for problem %d (%s)", idx, prob.get("title"))
            return None
        logger.debug("LLM raw for %d (%s): %s", idx, prob.get("title"), raw[:200])
        data: dict | None = None
        try:
            data = json.loads(strip_fences(raw))
        except json.JSONDecodeError:
            try:
                import json_repair  # type: ignore
                data = json_repair.loads(strip_fences(raw))
            except Exception:
                pass
        if not isinstance(data, dict):
            logger.warning("JSON parse failed for problem %d (%s): %s", idx, prob.get("title"), raw[:500])
            return None

        # Map neenza fields → internal format
        topics = prob.get("topics") or []
        category = topics[0] if topics else "General"

        # Normalise difficulty
        diff = (prob.get("difficulty") or "Medium").strip().capitalize()
        if diff not in ("Easy", "Medium", "Hard"):
            diff = "Medium"

        # Convert example objects to simple dicts if needed
        # neenza schema uses example_text (pre-formatted string), not input/output
        examples: list[dict] = []
        for ex in (prob.get("examples") or []):
            if isinstance(ex, dict):
                text = ex.get("example_text") or ""
                examples.append({"input": str(ex.get("input", text)), "output": str(ex.get("output", ""))})
            else:
                examples.append({"input": str(ex), "output": ""})

        # hints: use hints array from neenza (list of strings)
        hints = [str(h) for h in (prob.get("hints") or []) if h]

        # constraints: list of strings
        constraints = [str(c) for c in (prob.get("constraints") or []) if c]

        return {
            "id": idx,
            "title": prob.get("title", f"Problem {idx}"),
            "problem_description": (prob.get("description") or "")[:5000],
            "difficulty": diff,
            "category": category,
            "topics": topics,
            "examples": examples,
            "constraints": constraints,
            "hints": hints,
            "optimal_approach": str(data.get("optimal_approach") or "")[:2000],
            "python_code": str(data.get("python_code") or "")[:8000],
            "time_complexity": str(data.get("time_complexity") or "Unknown")[:50],
            "space_complexity": str(data.get("space_complexity") or "Unknown")[:50],
            "leetcode_url": prob.get("leetcode_url") or prob.get("url") or (
                f"https://leetcode.com/problems/{prob['problem_slug']}/"
                if prob.get("problem_slug") else ""
            ),
        }


# ── Download + load neenza dataset ───────────────────────────────────────────

async def load_source(source: str, client: httpx.AsyncClient) -> list[dict]:
    if source.startswith("http://") or source.startswith("https://"):
        logger.info("Downloading neenza dataset from %s", source)
        r = await client.get(source, timeout=120.0, follow_redirects=True)
        r.raise_for_status()
        data = r.json()
    else:
        p = Path(source)
        if not p.is_file():
            logger.error("Source file not found: %s", source)
            sys.exit(1)
        data = json.loads(p.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data
    # neenza wraps in {"questions": [...]}; also handle {"problems": [...]}
    if isinstance(data, dict):
        for key in ("questions", "problems"):
            if key in data and isinstance(data[key], list):
                return data[key]
    logger.error("Unexpected source format: expected list or {\"questions\": [...]}")
    sys.exit(1)


# ── Incremental save ──────────────────────────────────────────────────────────

def save(output_path: Path, results: list[dict]) -> None:
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved %d problems → %s", len(results), output_path)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate dsa_final_a_plus.json from neenza dataset")
    parser.add_argument("--source", default=NEENZA_URL, help="URL or local path to neenza JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON file path")
    parser.add_argument("--count", type=int, default=0, help="Max problems to process (0 = all)")
    parser.add_argument("--resume", action="store_true", help="Skip IDs already in output file")
    parser.add_argument("--concurrency", type=int, default=1, help="Max parallel LLM calls")
    args = parser.parse_args()

    # Auto-use local cache if source is the default URL and cache exists
    source = args.source
    if source == NEENZA_URL and NEENZA_LOCAL.is_file():
        logger.info("Using local cache: %s", NEENZA_LOCAL)
        source = str(NEENZA_LOCAL)

    output_path = Path(args.output)

    # Load existing output if resuming
    existing: list[dict] = []
    existing_ids: set[int] = set()
    if args.resume and output_path.is_file():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            existing_ids = {p["id"] for p in existing if "id" in p}
            logger.info("Resuming: %d problems already done", len(existing_ids))
        except Exception as exc:
            logger.warning("Could not load existing output: %s", exc)

    async with httpx.AsyncClient() as client:
        raw_problems = await load_source(source, client)
        logger.info("Loaded %d problems from source", len(raw_problems))

        # Apply --count limit
        if args.count and args.count > 0:
            raw_problems = raw_problems[: args.count]

        # Filter already-done (1-based IDs by position in neenza array)
        to_process = [
            (idx + 1, prob)
            for idx, prob in enumerate(raw_problems)
            if (idx + 1) not in existing_ids
        ]
        logger.info("%d problems to process", len(to_process))

        if not to_process:
            logger.info("Nothing to do.")
            return

        sem = asyncio.Semaphore(args.concurrency)
        results: list[dict] = list(existing)
        completed = 0

        running_tasks = [
            asyncio.ensure_future(enrich_problem(client, sem, prob, idx))
            for idx, prob in to_process
        ]

        try:
            for coro in asyncio.as_completed(running_tasks):
                enriched = await coro
                if enriched is not None:
                    results.append(enriched)
                completed += 1
                if completed % 5 == 0:
                    logger.info("Progress: %d / %d", completed, len(running_tasks))
                    save(output_path, sorted(results, key=lambda x: x.get("id", 0)))
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Interrupted — cancelling pending tasks…")
            for t in running_tasks:
                t.cancel()
            # Wait briefly for cancellations to propagate
            await asyncio.gather(*running_tasks, return_exceptions=True)
            logger.info("Saving %d results so far", len(results))

        # Final save — sorted by id
        results.sort(key=lambda x: x.get("id", 0))
        save(output_path, results)
        logger.info("Done. %d problems in %s", len(results), output_path)


if __name__ == "__main__":
    asyncio.run(main())
