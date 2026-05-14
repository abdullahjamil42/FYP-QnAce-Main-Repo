"""REST API for live coding round (Judge0 + Supabase + LLM)."""

from __future__ import annotations

import ast
import asyncio
import json
import logging
import re as _re
from pathlib import Path
from typing import Any, Optional, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import require_user
from ..config import get_settings
from ..intelligence.llm import call_llm, resolve_provider_config
from . import judge0_client, json_utils
from .supabase_data import (
    fetch_problem_row,
    fetch_problems_list,
    fetch_test_cases,
    patch_interview_session_coding_round,
)

logger = logging.getLogger("qace.coding.routes")

router = APIRouter(tags=["coding"])

# ── DSA problem bank from JSON file ──
_DSA_CACHE: list[dict[str, Any]] | None = None


def _load_dsa_problems() -> list[dict[str, Any]]:
    global _DSA_CACHE
    if _DSA_CACHE is not None:
        return _DSA_CACHE
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "dsa_final_a_plus.json",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "dsa_final_a_plus.json",
    ]
    for p in candidates:
        if p.is_file():
            _DSA_CACHE = json.loads(p.read_text(encoding="utf-8"))
            logger.info("Loaded %d DSA problems from %s", len(_DSA_CACHE), p)
            return _DSA_CACHE
    logger.warning("dsa_final_a_plus.json not found")
    _DSA_CACHE = []
    return _DSA_CACHE


# ── DSA test cases from separate JSON file (keyed by string problem ID) ──
_DSA_TESTS_CACHE: dict[str, dict] | None = None


def _load_dsa_test_cases() -> dict[str, dict]:
    global _DSA_TESTS_CACHE
    if _DSA_TESTS_CACHE is not None:
        return _DSA_TESTS_CACHE
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "dsa_test_cases.json",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "dsa_test_cases.json",
    ]
    for p in candidates:
        if p.is_file():
            _DSA_TESTS_CACHE = json.loads(p.read_text(encoding="utf-8"))
            logger.info("Loaded DSA test cases for %d problems", len(_DSA_TESTS_CACHE))
            return _DSA_TESTS_CACHE
    logger.warning("data/dsa_test_cases.json not found — DSA mode will use single-run fallback")
    _DSA_TESTS_CACHE = {}
    return _DSA_TESTS_CACHE


# ── Unified problem schema ──
class Problem(TypedDict, total=False):
    id: str
    title: str
    difficulty: str
    topics: list[str]
    description: str
    examples: list[Any]
    constraints: Any
    hints: list[str]
    benchmark_inputs: dict[str, str]  # {"n100": "...", "n1000": "...", "n10000": "..."}
    test_cases: list[dict[str, Any]]  # each: {stdin, expected_output, is_hidden}
    source: str  # "dsa" or "supabase"
    expected_complexity: str  # e.g. "O(n log n)"
    ref_code: str


def load_dsa_problem(problem_id: str) -> Problem:
    """Load a problem from the local DSA JSON bank."""
    try:
        pid = int(problem_id)
    except (ValueError, TypeError):
        pid = -1

    problems = _load_dsa_problems()
    prob = next((p for p in problems if p["id"] == pid), None)
    if not prob:
        raise HTTPException(status_code=404, detail="DSA problem not found")

    tc_data = _load_dsa_test_cases().get(str(pid), {})
    test_cases = tc_data.get("test_cases", [])
    bench = tc_data.get("complexity_benchmark_stdin", {})

    tc = prob.get("time_complexity", "")
    sc = prob.get("space_complexity", "")
    expected_complexity = f"{tc} time, {sc} space" if tc or sc else ""

    _hints: list[str] = list(prob.get("hints") or [])
    _approach = (prob.get("optimal_approach") or "").strip()
    if _approach and _approach not in _hints:
        _hints.append(_approach)
    _ref = (prob.get("python_code") or "").strip()
    if _ref:
        _hints.append(f"Reference solution:\n{_ref}")

    _raw_c = prob.get("constraints")
    if isinstance(_raw_c, list):
        constraints_out: Any = _raw_c
    elif isinstance(_raw_c, str) and _raw_c:
        constraints_out = [_raw_c]
    else:
        constraints_out = [expected_complexity] if expected_complexity else []

    return Problem(
        id=str(pid),
        title=prob.get("title", ""),
        difficulty=prob.get("difficulty", ""),
        topics=list(prob.get("topics") or [prob.get("category", "")]),
        description=_build_dsa_description(prob),
        examples=list(prob.get("examples") or []),
        constraints=constraints_out,
        hints=_hints,
        benchmark_inputs=bench if isinstance(bench, dict) else {},
        test_cases=test_cases,
        source="dsa",
        expected_complexity=expected_complexity,
        ref_code=_ref,
    )


def load_supabase_problem(problem_id: str, base: str, key: str) -> Problem:
    """Load a problem from Supabase (async — call with await in async context)."""
    # This is a sync stub; actual async loading is done inline in endpoint handlers
    # because it requires awaiting fetch_problem_row / fetch_test_cases.
    # Callers should use _load_supabase_problem_async instead.
    raise NotImplementedError("Use _load_supabase_problem_async")


async def _load_supabase_problem_async(problem_id: str, base: str, key: str) -> Problem:
    """Async version: fetch from Supabase and return a unified Problem."""
    prob = await fetch_problem_row(base, key, problem_id)
    if not prob:
        raise HTTPException(status_code=404, detail="Problem not found")
    tests = await fetch_test_cases(base, key, problem_id)

    bench = prob.get("complexity_benchmark_stdin") or {}
    return Problem(
        id=str(prob.get("id", problem_id)),
        title=prob.get("title", ""),
        difficulty=prob.get("difficulty", ""),
        topics=prob.get("topics") or [],
        description=prob.get("description", ""),
        examples=prob.get("examples") or [],
        constraints=prob.get("constraints"),
        hints=list(prob.get("hints") or []),
        benchmark_inputs=bench if isinstance(bench, dict) else {},
        test_cases=[
            {
                "stdin": t.get("stdin", ""),
                "expected_output": t.get("expected_output", ""),
                "is_hidden": t.get("is_hidden", False),
            }
            for t in sorted(tests or [], key=lambda x: x.get("sort_order", 0))
        ],
        source="supabase",
        expected_complexity="",
        ref_code="",
    )


# ── Output normalization (multi-step) ──
def _outputs_match(out: str, exp: str) -> bool:
    """Multi-step output normalization for pass/fail check."""
    # Step 1: strip whitespace
    o = out.strip()
    e = exp.strip()
    if o == e:
        return True

    # Step 2: collapse internal whitespace + lowercase
    o_norm = _re.sub(r"\s+", " ", o).lower()
    e_norm = _re.sub(r"\s+", " ", e).lower()
    if o_norm == e_norm:
        return True

    # Step 3: try JSON/Python list comparison (sorted)
    try:
        ol = json.loads(o)
        el = json.loads(e)
        if isinstance(ol, list) and isinstance(el, list):
            return sorted(str(x) for x in ol) == sorted(str(x) for x in el)
    except (json.JSONDecodeError, TypeError):
        pass

    # Step 4: try float comparison with tolerance
    try:
        of = float(o)
        ef = float(e)
        return abs(of - ef) <= 1e-6
    except (ValueError, TypeError):
        pass

    # Step 5: exact string fallback (already done above)
    return False


# ── Pre-submission static scan ──
def _static_scan(code: str) -> str | None:
    """Return an error message if code is rejected, else None."""
    if len(code.encode("utf-8")) > 50 * 1024:
        return "Submission exceeds 50 KB limit."

    forbidden = [
        ("fork(", "Use of fork() is not allowed."),
        ("os.fork", "Use of os.fork is not allowed."),
        ("subprocess", "Use of subprocess is not allowed."),
    ]
    for pattern, msg in forbidden:
        if pattern in code:
            return msg

    # exec/eval: reject if argument is non-trivial (not a simple string literal)
    for fname in ("exec", "eval"):
        for m in _re.finditer(rf"\b{fname}\s*\(", code):
            rest = code[m.end():]
            rest_stripped = rest.lstrip()
            # Allow eval("...") / exec("...") with simple string literal
            if rest_stripped.startswith(("'", '"', "b'", 'b"')):
                continue
            return f"Use of {fname}() with dynamic argument is not allowed."

    # while True: without break or return in body
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if not isinstance(node, ast.While):
                continue
            test = node.test
            # Check for `while True:`
            if not (isinstance(test, ast.Constant) and test.value is True):
                continue
            body_src = ast.dump(ast.Module(body=node.body, type_ignores=[]))
            if "Break" not in body_src and "Return" not in body_src:
                return "Infinite loop detected: while True without break or return."
    except SyntaxError:
        pass  # Let Judge0 report compile errors

    return None


# ── Adaptive benchmarking ──
async def _adaptive_benchmark(
    judge0_url: str,
    source_code: str,
    language_id: int,
    bench_inputs: dict[str, str],
) -> tuple[float | str | None, float | str | None, float | str | None]:
    """
    Probe benchmarks adaptively: n100 → n1000 → n10000.
    Returns (t_n100, t_n1000, t_n10000) where each value is:
      - float (seconds from Judge0)
      - "timeout" if the call timed out or Judge0 errored
      - None if no benchmark input is configured for that size
    """
    keys = ("n100", "n1000", "n10000")
    thresholds_ms = (10.0, 100.0)  # advance to next tier if below these
    results: list[float | str | None] = [None, None, None]

    for i, key in enumerate(keys):
        stdin_val = bench_inputs.get(key)
        if stdin_val is None:
            continue
        try:
            rb = await asyncio.wait_for(
                judge0_client.submit_once(
                    judge0_url,
                    source_code=source_code,
                    language_id=language_id,
                    stdin=str(stdin_val),
                    cpu_time_limit=3.0,
                    wait=True,
                ),
                timeout=10.0,
            )
            if rb.get("error"):
                results[i] = "timeout"
                break  # Don't probe larger sizes if smaller errored
            tv = rb.get("time")
            t_sec = float(tv) if tv is not None else None
            results[i] = t_sec
            if t_sec is not None and i < len(thresholds_ms):
                t_ms = t_sec * 1000.0
                if t_ms >= thresholds_ms[i]:
                    break  # Too slow; don't probe larger sizes
        except (asyncio.TimeoutError, Exception):
            results[i] = "timeout"
            break

    return (results[0], results[1], results[2])


# ── Robust LLM JSON parsing ──
async def _call_llm_json(
    messages: list[dict[str, str]],
    provider: Any,
    *,
    temperature: float = 0.2,
    max_tokens: int = 900,
    timeout_s: float = 45.0,
) -> dict[str, Any] | None:
    """
    Call LLM and parse JSON response robustly.
    - Attempts json_utils.extract_json on raw output.
    - Retries once with an explicit JSON instruction if parsing fails.
    - Logs json_parse_failure=True at ERROR level on double failure.
    - Returns None on failure (callers should fall back to heuristic).
    """
    raw: str | None = None
    try:
        raw = await call_llm(messages, provider, temperature=temperature, max_tokens=max_tokens, timeout_s=timeout_s)
    except Exception as exc:
        logger.warning("LLM call failed: %s", exc)
        return None

    if not raw:
        return None

    result = json_utils.extract_json(raw)
    if result is not None:
        return result

    # Retry with explicit JSON instruction
    retry_messages = list(messages) + [
        {"role": "user", "content": "Respond with only a valid JSON object, no explanation, no markdown."},
    ]
    raw2: str | None = None
    try:
        raw2 = await call_llm(retry_messages, provider, temperature=temperature, max_tokens=max_tokens, timeout_s=timeout_s)
    except Exception as exc:
        logger.warning("LLM retry call failed: %s", exc)

    if raw2:
        result2 = json_utils.extract_json(raw2)
        if result2 is not None:
            return result2

    logger.error(
        "json_parse_failure=True raw1=%s raw2=%s",
        (raw or "")[:500],
        (raw2 or "")[:500],
    )
    return None


class RunRequest(BaseModel):
    problem_id: str
    source_code: str
    language_id: int = 71
    session_id: str = ""
    source: str = ""  # "dsa" for local JSON problems
    custom_stdin: Optional[str] = None  # if set, run single custom test case


class SubmitRequest(BaseModel):
    problem_id: str
    source_code: str
    language_id: int = 71
    session_id: str = ""
    time_taken_seconds: Optional[float] = None
    reading_time_seconds: Optional[float] = None
    coding_time_seconds: Optional[float] = None
    source: str = ""


class AnalyzeRequest(BaseModel):
    problem_id: str
    source_code: str
    failed_test_cases: list[dict[str, Any]] = Field(default_factory=list)
    runtimes: Optional[dict[str, Any]] = None
    tier: int = 2  # 2 = failing tests, 3 = suboptimal but passing
    source: str = ""
    attempts: list[dict[str, Any]] = Field(default_factory=list)  # last 3 attempts history


def _settings_ok() -> tuple[str, str]:
    s = get_settings()
    base = (s.supabase_url or "").strip()
    key = (s.supabase_service_role_key or "").strip()
    if not base or not key:
        raise HTTPException(
            status_code=503,
            detail="Supabase service credentials not configured (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)",
        )
    return base, key


def _norm(s: str | None) -> str:
    if s is None:
        return ""
    return s.replace("\r\n", "\n").strip()


async def _run_judge(
    judge0_url: str,
    source_code: str,
    language_id: int,
    stdin: str,
    expected: str,
) -> dict[str, Any]:
    res = await judge0_client.submit_once(
        judge0_url,
        source_code=source_code,
        language_id=language_id,
        stdin=stdin,
        expected_output=None,
        wait=True,
    )
    if res.get("error"):
        logger.warning(
            "Judge0 run error: lang=%s stdin_len=%d err=%s detail=%s",
            language_id,
            len(stdin or ""),
            res.get("error"),
            str(res.get("detail") or "")[:200],
        )
        return {
            "stdin": stdin,
            "stdout": "",
            "stderr": res.get("detail", res.get("error")),
            "expected": _norm(expected),
            "passed": False,
            "time": None,
            "memory": None,
            "status": res.get("error"),
        }
    out = _norm(res.get("stdout", ""))
    exp = _norm(expected)
    passed = _outputs_match(out, exp)
    if not passed:
        logger.info(
            "Judge0 mismatch: lang=%s stdin_len=%d status=%s out=%s exp=%s",
            language_id,
            len(stdin or ""),
            res.get("status_description") or "",
            out[:120],
            exp[:120],
        )
    return {
        "stdin": stdin,
        "stdout": out,
        "stderr": res.get("stderr", ""),
        "expected": exp,
        "passed": passed,
        "time": res.get("time"),
        "memory": res.get("memory"),
        "status": res.get("status_description") or "",
    }


@router.get("/dsa/problems")
async def list_dsa_problems(
    difficulty: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    _user: Optional[str] = Depends(require_user),
):
    """List DSA problems from the local JSON bank."""
    problems = _load_dsa_problems()
    filtered = problems
    if difficulty:
        filtered = [p for p in filtered if p.get("difficulty", "").lower() == difficulty.lower()]
    if category:
        filtered = [p for p in filtered if p.get("category", "").lower() == category.lower()]
    return {
        "problems": [
            {
                "id": p["id"],
                "title": p["title"],
                "difficulty": p["difficulty"],
                "category": p["category"],
            }
            for p in filtered
        ]
    }


def _build_dsa_description(prob: dict[str, Any]) -> str:
    """Build a proper problem description from DSA JSON fields."""
    title = prob.get("title", "")
    desc = (prob.get("problem_description") or "").strip()
    code = (prob.get("python_code") or "").strip()
    approach = (prob.get("optimal_approach") or "").strip()
    url = (prob.get("leetcode_url") or "").strip()
    tc = prob.get("time_complexity", "")
    sc = prob.get("space_complexity", "")

    # Extract function signature from reference code
    sig_match = _re.search(r"def\s+(\w+)\(self,?\s*(.*?)\)\s*->\s*(.*?):", code)
    sig_line = ""
    if sig_match:
        fname, params, ret = sig_match.group(1), sig_match.group(2), sig_match.group(3)
        sig_line = f"def {fname}({params}) -> {ret}"

    parts: list[str] = []

    # If desc looks like a real description (> 80 chars and has sentences), use it
    if len(desc) > 80 and ("." in desc or ":" in desc):
        parts.append(desc)
    else:
        parts.append(f"Solve the \"{title}\" problem.")
        if desc and len(desc) > 10:
            parts.append(f"Hint: {desc}")

    if sig_line:
        parts.append(f"\nFunction signature:\n  {sig_line}")

    if approach:
        # Show first ~300 chars of approach as a guide
        preview = approach[:300]
        if len(approach) > 300:
            preview += "..."
        parts.append(f"\nApproach:\n{preview}")

    if tc or sc:
        parts.append(f"\nExpected complexity: {tc} time, {sc} space")

    if url:
        parts.append(f"\nLeetCode: {url}")

    return "\n".join(parts)


@router.get("/dsa/problems/{problem_id}")
async def get_dsa_problem(
    problem_id: int,
    _user: Optional[str] = Depends(require_user),
):
    """Get a single DSA problem formatted for CodingRoundView."""
    problems = _load_dsa_problems()
    prob = next((p for p in problems if p["id"] == problem_id), None)
    if not prob:
        raise HTTPException(status_code=404, detail="DSA problem not found")

    description = _build_dsa_description(prob)

    # Progressive hints: original LeetCode hints first, then approach, then reference code
    _hints: list[str] = list(prob.get("hints") or [])
    _approach = (prob.get("optimal_approach") or "").strip()
    if _approach and _approach not in _hints:
        _hints.append(_approach)
    _ref = (prob.get("python_code") or "").strip()
    if _ref:
        _hints.append(f"Reference solution:\n{_ref}")

    _raw_c = prob.get("constraints")
    if isinstance(_raw_c, list):
        _constraints_out: Any = _raw_c
    elif isinstance(_raw_c, str) and _raw_c:
        _constraints_out = [_raw_c]
    else:
        _constraints_out = [f"Expected: {prob.get('time_complexity', '')} time, {prob.get('space_complexity', '')} space"]

    return {
        "id": str(prob["id"]),
        "title": prob["title"],
        "difficulty": prob["difficulty"],
        "topics": list(prob.get("topics") or [prob.get("category", "")]),
        "description": description,
        "examples": list(prob.get("examples") or []),
        "constraints": _constraints_out,
        "hints": _hints,
        "reference_solution": prob.get("python_code", ""),
        "time_complexity": prob.get("time_complexity", ""),
        "space_complexity": prob.get("space_complexity", ""),
        "source": "dsa",
    }


@router.post("/interview/run")
async def interview_run(
    body: RunRequest,
    _user: Optional[str] = Depends(require_user),
):
    s = get_settings()
    judge0_url = (s.judge0_api_url or "").strip()
    if not judge0_url:
        raise HTTPException(status_code=503, detail="JUDGE0_API_URL not configured")

    # ── Static scan (applies to all modes) ──
    scan_err = _static_scan(body.source_code)
    if scan_err:
        raise HTTPException(status_code=400, detail=scan_err)

    # ── Custom input mode ──
    if body.custom_stdin is not None:
        try:
            res = await judge0_client.submit_once(
                judge0_url,
                source_code=body.source_code,
                language_id=body.language_id,
                stdin=body.custom_stdin,
                expected_output=None,
                wait=True,
            )
            return {
                "results": [
                    {
                        "stdin": body.custom_stdin,
                        "stdout": _norm(res.get("stdout", "")),
                        "stderr": res.get("stderr", ""),
                        "expected": "",
                        "passed": not res.get("error") and not res.get("stderr"),
                        "time": res.get("time"),
                        "memory": res.get("memory"),
                        "status": res.get("status_description", ""),
                    }
                ]
            }
        except Exception as exc:
            return {
                "results": [
                    {
                        "stdin": body.custom_stdin,
                        "stdout": "",
                        "stderr": str(exc),
                        "expected": "",
                        "passed": False,
                        "time": None,
                        "memory": None,
                        "status": "error",
                    }
                ]
            }

    # DSA mode: run visible test cases (falls back to compile-check if none generated yet)
    if body.source == "dsa":
        try:
            pid = int(body.problem_id)
        except (ValueError, TypeError):
            pid = -1
        tc_data = _load_dsa_test_cases().get(str(pid), {})
        visible_tests = [t for t in tc_data.get("test_cases", []) if not t.get("is_hidden", False)]

        if not visible_tests:
            # Graceful fallback: test cases not yet generated — just compile-check the code
            try:
                res = await judge0_client.submit_once(
                    judge0_url,
                    source_code=body.source_code,
                    language_id=body.language_id,
                    stdin="",
                    expected_output=None,
                    wait=True,
                )
                stdout = _norm(res.get("stdout", ""))
                stderr = res.get("stderr", "")
                status = res.get("status_description", "")
                return {
                    "results": [
                        {
                            "stdin": "",
                            "stdout": stdout,
                            "stderr": stderr,
                            "expected": "",
                            "passed": not res.get("error") and not stderr,
                            "time": res.get("time"),
                            "memory": res.get("memory"),
                            "status": status,
                        }
                    ]
                }
            except Exception as exc:
                return {
                    "results": [
                        {
                            "stdin": "",
                            "stdout": "",
                            "stderr": str(exc),
                            "expected": "",
                            "passed": False,
                            "time": None,
                            "memory": None,
                            "status": "error",
                        }
                    ]
                }

        results: list[dict[str, Any]] = []
        for t in visible_tests:
            try:
                row = await _run_judge(
                    judge0_url,
                    body.source_code,
                    body.language_id,
                    t.get("stdin", ""),
                    t.get("expected_output", ""),
                )
                results.append(row)
            except Exception as exc:
                logger.warning("DSA run case failed: %s", exc)
                results.append(
                    {
                        "stdin": t.get("stdin", ""),
                        "stdout": "",
                        "stderr": str(exc),
                        "expected": _norm(t.get("expected_output", "")),
                        "passed": False,
                        "time": None,
                        "memory": None,
                        "status": "error",
                    }
                )
        return {"results": results}

    base, key = _settings_ok()
    tests = await fetch_test_cases(base, key, body.problem_id, hidden=False)
    if not tests:
        raise HTTPException(status_code=404, detail="No public test cases for problem")

    results: list[dict[str, Any]] = []
    for t in sorted(tests, key=lambda x: x.get("sort_order", 0)):
        try:
            row = await _run_judge(
                judge0_url,
                body.source_code,
                body.language_id,
                t.get("stdin", ""),
                t.get("expected_output", ""),
            )
            results.append(row)
        except Exception as exc:
            logger.warning("run case failed: %s", exc)
            results.append(
                {
                    "stdin": t.get("stdin", ""),
                    "stdout": "",
                    "stderr": str(exc),
                    "expected": _norm(t.get("expected_output", "")),
                    "passed": False,
                    "time": None,
                    "memory": None,
                    "status": "error",
                }
            )
    return {"results": results}


def _dsa_heuristic_score(
    student_code: str, ref_code: str, prob: dict[str, Any], code_ran: bool,
) -> dict[str, Any]:
    """Heuristic scoring for DSA problems when LLM is unavailable."""
    observations: list[str] = []
    score = 0
    tc = prob.get("time_complexity", "Unknown")
    sc = prob.get("space_complexity", "Unknown")

    # Extract the expected function name from reference code
    ref_func = _re.search(r"def\s+(\w+)\(self", ref_code)
    func_name = ref_func.group(1) if ref_func else None

    # Check if student code addresses the problem at all
    has_class = "class Solution" in student_code or "class " in student_code
    has_func = func_name and func_name in student_code if func_name else False
    has_return = "return " in student_code
    code_lines = [l for l in student_code.strip().split("\n") if l.strip() and not l.strip().startswith("#")]
    line_count = len(code_lines)

    # Scoring rubric (0-10)
    if not code_ran:
        observations.append("Code has runtime errors.")
        score = 1
    elif line_count < 3:
        observations.append("Code is too short — does not appear to solve the problem.")
        score = 1
    else:
        if has_func or has_class:
            score += 3
            observations.append("Correct function/class structure detected.")
        else:
            score += 1
            observations.append("Missing expected function/class structure.")

        if has_return:
            score += 2
            observations.append("Contains return statement.")
        else:
            observations.append("No return statement found — likely incomplete.")

        # Check for key patterns from the reference
        ref_keywords = set(_re.findall(r"\b(?:sort|set|dict|heap|stack|deque|queue|defaultdict|Counter|bisect|dfs|bfs|dp|memo)\b", ref_code.lower()))
        student_keywords = set(_re.findall(r"\b(?:sort|set|dict|heap|stack|deque|queue|defaultdict|Counter|bisect|dfs|bfs|dp|memo)\b", student_code.lower()))
        overlap = ref_keywords & student_keywords
        if overlap:
            score += 2
            observations.append(f"Uses relevant data structures/algorithms: {', '.join(sorted(overlap))}.")
        elif ref_keywords:
            observations.append(f"Missing expected patterns: {', '.join(sorted(ref_keywords))}.")

        # Length comparison — rough check for effort
        if line_count >= 5:
            score += 1

    score = max(1, min(10, score))

    return {
        "time_complexity": tc,
        "space_complexity": sc,
        "complexity_explanation": f"Expected {tc} time, {sc} space based on problem requirements. LLM unavailable for detailed analysis.",
        "is_optimal": False,
        "optimal_complexity": tc,
        "approach_identified": "Heuristic analysis (LLM unavailable)",
        "quality_observations": observations,
        "quality_score": score,
    }


def _fallback_llm_json() -> dict[str, Any]:
    return {
        "time_complexity": "Unknown",
        "space_complexity": "Unknown",
        "complexity_explanation": "Analysis unavailable.",
        "is_optimal": True,
        "optimal_complexity": "Unknown",
        "approach_identified": "Unknown",
        "quality_observations": [],
        "quality_score": 5,
    }


@router.post("/interview/submit")
async def interview_submit(
    body: SubmitRequest,
    _user: Optional[str] = Depends(require_user),
):
    s = get_settings()
    judge0_url = (s.judge0_api_url or "").strip()
    if not judge0_url:
        raise HTTPException(status_code=503, detail="JUDGE0_API_URL not configured")

    # ── Static scan ──
    scan_err = _static_scan(body.source_code)
    if scan_err:
        raise HTTPException(status_code=400, detail=scan_err)

    # ── DSA mode ──
    if body.source == "dsa":
        problem = load_dsa_problem(body.problem_id)
        all_tests = problem.get("test_cases", [])
        ref_code = problem.get("ref_code", "")
        student_code = body.source_code.strip()

        # ── Correctness: run all test cases (visible + hidden) ──
        if all_tests:
            dsa_failed: list[dict[str, Any]] = []
            dsa_passed = 0
            for t in all_tests:
                try:
                    row = await _run_judge(
                        judge0_url,
                        body.source_code,
                        body.language_id,
                        t.get("stdin", ""),
                        t.get("expected_output", ""),
                    )
                    if row.get("passed"):
                        dsa_passed += 1
                    else:
                        dsa_failed.append(
                            {
                                "stdin": row.get("stdin"),
                                "expected": row.get("expected"),
                                "actual": row.get("stdout"),
                                "is_hidden": t.get("is_hidden", False),
                            }
                        )
                except Exception as exc:
                    dsa_failed.append(
                        {
                            "stdin": t.get("stdin"),
                            "expected": t.get("expected_output"),
                            "actual": "",
                            "error": str(exc),
                            "is_hidden": t.get("is_hidden", False),
                        }
                    )
            correctness: dict[str, Any] = {
                "passed": dsa_passed,
                "total": len(all_tests),
                "failed_cases": dsa_failed,
            }
            total_hidden = sum(1 for t in all_tests if t.get("is_hidden"))
            passed_hidden = sum(
                1 for t, r in zip(
                    all_tests,
                    [{"passed": dsa_passed > 0}] * len(all_tests),  # placeholder; recompute below
                )
                if t.get("is_hidden")
            )
            # Recompute properly: track per-test pass for hidden tests
            passed_hidden = sum(
                1 for t in all_tests
                if t.get("is_hidden") and not any(
                    f.get("stdin") == t.get("stdin") for f in dsa_failed
                )
            )
            code_ran = dsa_passed > 0 or len(dsa_failed) == 0
        else:
            # Fallback: single run when test cases not generated yet
            run_res = await judge0_client.submit_once(
                judge0_url,
                source_code=body.source_code,
                language_id=body.language_id,
                stdin="",
                expected_output=None,
                wait=True,
            )
            has_error = bool(run_res.get("error") or run_res.get("stderr"))
            code_ran = not has_error
            correctness = {
                "passed": 1 if code_ran else 0,
                "total": 1,
                "failed_cases": [] if code_ran else [
                    {"stdin": "", "expected": "", "actual": run_res.get("stderr", ""), "error": run_res.get("error", "")}
                ],
            }
            total_hidden = 0
            passed_hidden = 0

        # ── Adaptive benchmark ──
        bench_inputs = problem.get("benchmark_inputs", {})
        t100, t1000, t10000 = await _adaptive_benchmark(
            judge0_url, body.source_code, body.language_id, bench_inputs
        )

        # ── LLM scoring ──
        provider = resolve_provider_config(s)
        llm_out: dict[str, Any] | None = None
        if provider:
            expected_complexity = problem.get("expected_complexity", "")
            prompt_user = (
                f"Problem: {problem.get('title', '')}\n"
                f"Expected complexity: {expected_complexity}\n"
                f"Runtimes (seconds, Judge0): n=100→{t100}, n=1000→{t1000}, n=10000→{t10000}\n\n"
                f"Student code:\n```\n{body.source_code[:12000]}\n```\n"
            )
            system = """You are a senior software engineer reviewing interview code.
Return ONLY valid JSON (no markdown, no extra text):
{
  "time_complexity": "O(n)",
  "space_complexity": "O(1)",
  "complexity_explanation": "...",
  "is_optimal": false,
  "optimal_complexity": "O(n)",
  "approach_identified": "...",
  "quality_observations": ["..."],
  "quality_score": 6
}"""
            llm_out = await _call_llm_json(
                [{"role": "system", "content": system}, {"role": "user", "content": prompt_user}],
                provider,
                temperature=0.2,
                max_tokens=900,
                timeout_s=45.0,
            )

        if llm_out is None:
            llm_out = _dsa_heuristic_score(student_code, ref_code, problem, code_ran)

        return {
            "correctness": correctness,
            "complexity": {
                "time": llm_out.get("time_complexity", "Unknown"),
                "space": llm_out.get("space_complexity", "Unknown"),
                "is_optimal": bool(llm_out.get("is_optimal", False)),
                "optimal": llm_out.get("optimal_complexity", problem.get("expected_complexity", "Unknown")),
                "explanation": llm_out.get("complexity_explanation", ""),
            },
            "quality": {
                "observations": list(llm_out.get("quality_observations") or []),
                "score": int(llm_out.get("quality_score") or 1),
            },
            "time_taken_seconds": int(body.time_taken_seconds or 0),
            "empirical_ms": {"n100": t100, "n1000": t1000, "n10000": t10000},
            "hidden_summary": {"total_hidden": total_hidden, "passed_hidden": passed_hidden},
        }

    # ── Supabase mode ──
    base, key = _settings_ok()
    problem_sb = await _load_supabase_problem_async(body.problem_id, base, key)
    all_tests_sb = problem_sb.get("test_cases", [])
    if not all_tests_sb:
        raise HTTPException(status_code=404, detail="No test cases")

    failed: list[dict[str, Any]] = []
    passed_n = 0
    for t in all_tests_sb:
        try:
            row = await _run_judge(
                judge0_url,
                body.source_code,
                body.language_id,
                t.get("stdin", ""),
                t.get("expected_output", ""),
            )
            if row.get("passed"):
                passed_n += 1
            else:
                failed.append(
                    {
                        "stdin": row.get("stdin"),
                        "expected": row.get("expected"),
                        "actual": row.get("stdout"),
                        "is_hidden": t.get("is_hidden", False),
                    }
                )
        except Exception as exc:
            failed.append(
                {
                    "stdin": t.get("stdin"),
                    "expected": t.get("expected_output"),
                    "actual": "",
                    "error": str(exc),
                    "is_hidden": t.get("is_hidden", False),
                }
            )

    total_hidden_sb = sum(1 for t in all_tests_sb if t.get("is_hidden"))
    passed_hidden_sb = sum(
        1 for t in all_tests_sb
        if t.get("is_hidden") and not any(f.get("stdin") == t.get("stdin") for f in failed)
    )

    # ── Adaptive benchmark ──
    bench_inputs_sb = problem_sb.get("benchmark_inputs", {})
    t100_sb, t1000_sb, t10000_sb = await _adaptive_benchmark(
        judge0_url, body.source_code, body.language_id, bench_inputs_sb
    )

    # ── LLM scoring ──
    provider = resolve_provider_config(s)
    llm_out_sb: dict[str, Any] = _fallback_llm_json()
    if provider:
        prompt_user_sb = (
            f"Problem: {problem_sb.get('title', '')}\n\n"
            f"Code:\n```\n{body.source_code[:12000]}\n```\n\n"
            f"Runtimes (seconds, Judge0): n=100→{t100_sb}, n=1000→{t1000_sb}, n=10000→{t10000_sb}\n"
        )
        system_sb = """You are a senior software engineer reviewing interview code.
Return ONLY valid JSON (no markdown, no extra text):
{
  "time_complexity": "O(n)",
  "space_complexity": "O(1)",
  "complexity_explanation": "...",
  "is_optimal": false,
  "optimal_complexity": "O(n)",
  "approach_identified": "...",
  "quality_observations": ["..."],
  "quality_score": 6
}"""
        result_sb = await _call_llm_json(
            [{"role": "system", "content": system_sb}, {"role": "user", "content": prompt_user_sb}],
            provider,
            temperature=0.2,
            max_tokens=900,
            timeout_s=45.0,
        )
        if result_sb is not None:
            llm_out_sb = result_sb

    scoring: dict[str, Any] = {
        "correctness": {
            "passed": passed_n,
            "total": len(all_tests_sb),
            "failed_cases": failed,
        },
        "complexity": {
            "time": llm_out_sb.get("time_complexity", "Unknown"),
            "space": llm_out_sb.get("space_complexity", "Unknown"),
            "is_optimal": bool(llm_out_sb.get("is_optimal", True)),
            "optimal": llm_out_sb.get("optimal_complexity", "Unknown"),
            "explanation": llm_out_sb.get("complexity_explanation", ""),
        },
        "quality": {
            "observations": list(llm_out_sb.get("quality_observations") or []),
            "score": int(llm_out_sb.get("quality_score") or 5),
        },
        "time_taken_seconds": int(body.time_taken_seconds or 0),
        "empirical_ms": {"n100": t100_sb, "n1000": t1000_sb, "n10000": t10000_sb},
        "hidden_summary": {"total_hidden": total_hidden_sb, "passed_hidden": passed_hidden_sb},
    }

    if body.session_id and scoring:
        await patch_interview_session_coding_round(
            base,
            key,
            webrtc_session_id=body.session_id,
            coding_round=scoring,
        )

    return scoring


@router.get("/interview/hint")
async def interview_hint(
    problem_id: str = Query(...),
    hint_index: int = Query(0, ge=0),
    source: str = Query(""),
    _user: Optional[str] = Depends(require_user),
):
    # DSA mode: hints from local JSON
    if source == "dsa":
        problems = _load_dsa_problems()
        try:
            pid = int(problem_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Invalid DSA problem id")
        prob = next((p for p in problems if p["id"] == pid), None)
        if not prob:
            raise HTTPException(status_code=404, detail="DSA problem not found")
        # Progressive hints: original LeetCode hints first (gentlest), then approach, then reference code
        dsa_hints: list[str] = list(prob.get("hints") or [])
        _approach_h = (prob.get("optimal_approach") or "").strip()
        _ref_h = (prob.get("python_code") or "").strip()
        if _approach_h and _approach_h not in dsa_hints:
            dsa_hints.append(_approach_h)
        if _ref_h:
            dsa_hints.append(f"Reference solution:\n{_ref_h}")
        if not dsa_hints:
            raise HTTPException(status_code=404, detail="No hints available")
        idx = min(hint_index, len(dsa_hints) - 1)
        return {"hint": dsa_hints[idx], "hint_index": idx, "total_hints": len(dsa_hints)}

    base, key = _settings_ok()
    prob = await fetch_problem_row(base, key, problem_id)
    if not prob:
        raise HTTPException(status_code=404, detail="Problem not found")
    hints = prob.get("hints") or []
    if not isinstance(hints, list):
        hints = []
    if hint_index >= len(hints):
        raise HTTPException(status_code=404, detail="Hint not available")
    return {"hint": hints[hint_index], "hint_index": hint_index, "total_hints": len(hints)}


@router.post("/interview/analyze")
async def interview_analyze(
    body: AnalyzeRequest,
    _user: Optional[str] = Depends(require_user),
):
    s = get_settings()

    # DSA mode: use local JSON for problem context
    if body.source == "dsa":
        problems = _load_dsa_problems()
        try:
            pid = int(body.problem_id)
        except ValueError:
            pid = -1
        dsa_prob = next((p for p in problems if p["id"] == pid), None)
        title = dsa_prob["title"] if dsa_prob else "Problem"
        extra_ctx = ""
        if dsa_prob:
            extra_ctx = f"\nExpected: {dsa_prob.get('time_complexity', '')} time, {dsa_prob.get('space_complexity', '')} space\n"
    else:
        base, key = _settings_ok()
        prob = await fetch_problem_row(base, key, body.problem_id)
        title = (prob or {}).get("title", "Problem")
        extra_ctx = ""

    provider = resolve_provider_config(s)
    tier = 3 if body.tier >= 3 else 2

    # Build attempts history prefix
    attempts_prefix = ""
    if body.attempts:
        n = len(body.attempts)
        snippets = []
        for i, a in enumerate(body.attempts[-3:], 1):
            code_snap = str(a.get("code", ""))[:800]
            outcome = "passed" if a.get("passed") else "failed"
            snippets.append(f"  Attempt {i}/{n} ({outcome}):\n{code_snap}")
        attempts_prefix = f"Previous {n} attempt(s):\n" + "\n".join(snippets) + "\n\n"

    if tier == 2:
        user_msg = (
            f"Problem: {title}\n{extra_ctx}"
            f"{attempts_prefix}"
            f"Failed tests: {json.dumps(body.failed_test_cases)[:4000]}\n"
            f"Code snippet:\n{body.source_code[:6000]}\n"
            "Give ONE short actionable hint (2-3 sentences). No code solution."
        )
    else:
        user_msg = (
            f"Problem: {title}\n{extra_ctx}"
            f"{attempts_prefix}"
            f"Runtimes: {json.dumps(body.runtimes or {})}\n"
            f"Code:\n{body.source_code[:6000]}\n"
            "The solution passes tests but may be suboptimal. Give ONE short nudge toward optimal complexity (2-3 sentences)."
        )
    system = "You are an interview coach. Reply with plain text only, no JSON."

    message = "Keep going — revisit edge cases and complexity."
    if provider:
        try:
            raw = await call_llm(
                [{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
                provider,
                temperature=0.4,
                max_tokens=280,
                timeout_s=25.0,
            )
            if raw:
                message = raw.strip()
        except Exception as exc:
            logger.warning("analyze LLM failed: %s", exc)

    return {"tier": tier, "message": message}


@router.get("/problems")
async def list_problems(
    difficulty: Optional[str] = Query(None),
    _user: Optional[str] = Depends(require_user),
):
    """List available coding problems."""
    base, key = _settings_ok()
    problems = await fetch_problems_list(base, key, difficulty=difficulty)
    return {"problems": problems}


@router.get("/problems/{problem_id}")
async def get_problem(
    problem_id: str,
    _user: Optional[str] = Depends(require_user),
):
    base, key = _settings_ok()
    prob = await fetch_problem_row(base, key, problem_id)
    if not prob:
        raise HTTPException(status_code=404, detail="Problem not found")
    # Strip internal fields if any
    return {
        "id": prob.get("id"),
        "title": prob.get("title"),
        "difficulty": prob.get("difficulty"),
        "topics": prob.get("topics"),
        "description": prob.get("description"),
        "examples": prob.get("examples"),
        "constraints": prob.get("constraints"),
        "hints": prob.get("hints"),
        "source": "supabase",
    }
