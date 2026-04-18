"""REST API for live coding round (Judge0 + Supabase + LLM)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

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


class RunRequest(BaseModel):
    problem_id: str
    source_code: str
    language_id: int = 71
    session_id: str = ""
    source: str = ""  # "dsa" for local JSON problems


class SubmitRequest(BaseModel):
    problem_id: str
    source_code: str
    language_id: int = 71
    session_id: str = ""
    time_taken_seconds: Optional[float] = None
    source: str = ""


class AnalyzeRequest(BaseModel):
    problem_id: str
    source_code: str
    failed_test_cases: list[dict[str, Any]] = Field(default_factory=list)
    runtimes: Optional[dict[str, Any]] = None
    tier: int = 2  # 2 = failing tests, 3 = suboptimal but passing
    source: str = ""


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
    passed = out == exp
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


import re as _re


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
async def get_dsa_problem(problem_id: int):
    """Get a single DSA problem formatted for CodingRoundView."""
    problems = _load_dsa_problems()
    prob = next((p for p in problems if p["id"] == problem_id), None)
    if not prob:
        raise HTTPException(status_code=404, detail="DSA problem not found")

    description = _build_dsa_description(prob)

    return {
        "id": str(prob["id"]),
        "title": prob["title"],
        "difficulty": prob["difficulty"],
        "topics": [prob["category"]],
        "description": description,
        "examples": [],
        "constraints": f"Expected: {prob['time_complexity']} time, {prob['space_complexity']} space",
        "hints": [prob.get("optimal_approach", "")[:500]] if prob.get("optimal_approach") else [],
        "reference_solution": prob.get("python_code", ""),
        "time_complexity": prob.get("time_complexity", ""),
        "space_complexity": prob.get("space_complexity", ""),
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

    # DSA mode: run code without test-case validation (no test cases in JSON bank)
    if body.source == "dsa":
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

    # ── DSA mode: LLM-only analysis (no Supabase test cases) ──
    if body.source == "dsa":
        problems = _load_dsa_problems()
        try:
            pid = int(body.problem_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Invalid DSA problem id")
        prob = next((p for p in problems if p["id"] == pid), None)
        if not prob:
            raise HTTPException(status_code=404, detail="DSA problem not found")

        # Run code once to capture output
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

        ref_code = (prob.get("python_code") or "").strip()
        student_code = body.source_code.strip()

        provider = resolve_provider_config(s)
        llm_out: dict[str, Any] | None = None
        if provider:
            prompt_user = (
                f"Problem: {prob['title']}\n"
                f"Category: {prob.get('category', '')}\n"
                f"Expected complexity: {prob.get('time_complexity', '')} time, {prob.get('space_complexity', '')} space\n"
                f"Reference approach: {prob.get('optimal_approach', '')[:2000]}\n\n"
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
            try:
                raw = await call_llm(
                    [{"role": "system", "content": system}, {"role": "user", "content": prompt_user}],
                    provider,
                    temperature=0.2,
                    max_tokens=900,
                    timeout_s=45.0,
                )
                if raw:
                    cleaned = json_utils.strip_markdown_fences(raw)
                    llm_out = json.loads(cleaned)
            except Exception as exc:
                logger.warning("DSA LLM scoring failed: %s", exc)

        # Heuristic fallback when LLM is unavailable
        if llm_out is None:
            llm_out = _dsa_heuristic_score(student_code, ref_code, prob, code_ran)

        return {
            "correctness": {
                "passed": 1 if code_ran else 0,
                "total": 1,
                "failed_cases": [] if code_ran else [{"stdin": "", "expected": "", "actual": run_res.get("stderr", ""), "error": run_res.get("error", "")}],
            },
            "complexity": {
                "time": llm_out.get("time_complexity", "Unknown"),
                "space": llm_out.get("space_complexity", "Unknown"),
                "is_optimal": bool(llm_out.get("is_optimal", False)),
                "optimal": llm_out.get("optimal_complexity", prob.get("time_complexity", "Unknown")),
                "explanation": llm_out.get("complexity_explanation", ""),
            },
            "quality": {
                "observations": list(llm_out.get("quality_observations") or []),
                "score": int(llm_out.get("quality_score") or 1),
            },
            "time_taken_seconds": int(body.time_taken_seconds or 0),
            "empirical_ms": {"n100": None, "n1000": None, "n10000": None},
        }

    base, key = _settings_ok()

    prob = await fetch_problem_row(base, key, body.problem_id)
    if not prob:
        raise HTTPException(status_code=404, detail="Problem not found")

    tests = await fetch_test_cases(base, key, body.problem_id)
    if not tests:
        raise HTTPException(status_code=404, detail="No test cases")

    failed: list[dict[str, Any]] = []
    passed_n = 0
    for t in sorted(tests, key=lambda x: x.get("sort_order", 0)):
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

    bench = prob.get("complexity_benchmark_stdin") or {}
    t100 = t1000 = t10000 = None
    if isinstance(bench, dict):
        keys = ("n100", "n1000", "n10000")
        vals: list[tuple[str, Optional[float]]] = []
        for k in keys:
            stdin_val = bench.get(k)
            if stdin_val is None:
                vals.append((k, None))
                continue
            try:
                rbench = await judge0_client.submit_once(
                    judge0_url,
                    source_code=body.source_code,
                    language_id=body.language_id,
                    stdin=str(stdin_val),
                    wait=True,
                )
                if rbench.get("error"):
                    vals.append((k, None))
                else:
                    tv = rbench.get("time")
                    try:
                        vals.append((k, float(tv) if tv is not None else None))
                    except (TypeError, ValueError):
                        vals.append((k, None))
            except Exception:
                vals.append((k, None))
        t100 = vals[0][1] if len(vals) > 0 else None
        t1000 = vals[1][1] if len(vals) > 1 else None
        t10000 = vals[2][1] if len(vals) > 2 else None

    provider = resolve_provider_config(s)
    llm_out: dict[str, Any] = _fallback_llm_json()
    if provider:
        prompt_user = (
            f"Problem: {prob.get('title', '')}\n\n"
            f"Code:\n```\n{body.source_code[:12000]}\n```\n\n"
            f"Runtimes (ms, Judge0 time field): n=100→{t100}, n=1000→{t1000}, n=10000→{t10000}\n"
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
        try:
            raw = await call_llm(
                [{"role": "system", "content": system}, {"role": "user", "content": prompt_user}],
                provider,
                temperature=0.2,
                max_tokens=900,
                timeout_s=45.0,
            )
            if raw:
                cleaned = json_utils.strip_markdown_fences(raw)
                llm_out = json.loads(cleaned)
        except Exception as exc:
            logger.warning("LLM scoring parse failed: %s", exc)

    scoring: dict[str, Any] = {
        "correctness": {
            "passed": passed_n,
            "total": len(tests),
            "failed_cases": failed,
        },
        "complexity": {
            "time": llm_out.get("time_complexity", "Unknown"),
            "space": llm_out.get("space_complexity", "Unknown"),
            "is_optimal": bool(llm_out.get("is_optimal", True)),
            "optimal": llm_out.get("optimal_complexity", "Unknown"),
            "explanation": llm_out.get("complexity_explanation", ""),
        },
        "quality": {
            "observations": list(llm_out.get("quality_observations") or []),
            "score": int(llm_out.get("quality_score") or 5),
        },
        "time_taken_seconds": int(body.time_taken_seconds or 0),
        "empirical_ms": {"n100": t100, "n1000": t1000, "n10000": t10000},
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
        approach = prob.get("optimal_approach", "")
        ref_code = prob.get("python_code", "")
        hints = []
        if approach:
            hints.append(approach[:500])
        if len(approach) > 500:
            hints.append(approach[500:])
        if ref_code:
            hints.append(f"Reference solution:\n{ref_code}")
        if not hints:
            raise HTTPException(status_code=404, detail="No hints available")
        idx = min(hint_index, len(hints) - 1)
        return {"hint": hints[idx], "hint_index": idx, "total_hints": len(hints)}

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
    if tier == 2:
        user_msg = (
            f"Problem: {title}\n{extra_ctx}"
            f"Failed tests: {json.dumps(body.failed_test_cases)[:4000]}\n"
            f"Code snippet:\n{body.source_code[:6000]}\n"
            "Give ONE short actionable hint (2-3 sentences). No code solution."
        )
    else:
        user_msg = (
            f"Problem: {title}\n{extra_ctx}"
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
    }
