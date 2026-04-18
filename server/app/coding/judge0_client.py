"""Submit code to Judge0 CE and wait for results."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("qace.coding.judge0")


def _norm_out(s: str | None) -> str:
    if s is None:
        return ""
    return s.replace("\r\n", "\n").strip()


async def submit_once(
    base_url: str,
    *,
    source_code: str,
    language_id: int,
    stdin: str,
    expected_output: str | None = None,
    cpu_time_limit: float = 2.0,
    memory_limit: int = 128_000,
    wait: bool = True,
) -> dict[str, Any]:
    """
    Create a submission with wait=true and return normalized stdout/stderr/time/memory/status.
    """
    url = base_url.rstrip("/")
    payload: dict[str, Any] = {
        "source_code": source_code,
        "language_id": language_id,
        "stdin": stdin,
        "cpu_time_limit": cpu_time_limit,
        "memory_limit": memory_limit,
    }
    if expected_output is not None:
        payload["expected_output"] = expected_output

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(
                f"{url}/submissions",
                params={"base64_encoded": "false", "wait": "true" if wait else "false"},
                json=payload,
            )
            if r.status_code >= 400:
                logger.warning("Judge0 POST failed: %s %s", r.status_code, r.text[:400])
                return {"error": f"judge0_http_{r.status_code}", "detail": r.text[:500]}

            sub = r.json()
            if not isinstance(sub, dict):
                return {"error": "invalid_response", "detail": str(sub)[:200]}
            return _normalize_submission(sub, expected_output)
    except Exception as exc:
        logger.warning("Judge0 submit failed: %s", exc)
        return {"error": "exception", "detail": str(exc)[:300]}


def _normalize_submission(sub: dict[str, Any], expected_output: str | None) -> dict[str, Any]:
    stdout = sub.get("stdout")
    out = _norm_out(str(stdout) if stdout is not None else "")
    stderr = sub.get("stderr") or ""
    cout = sub.get("compile_output") or ""
    err = _norm_out(str(stderr))
    comp = _norm_out(str(cout))
    time_val = sub.get("time")
    mem = sub.get("memory")
    status = sub.get("status") or {}
    status_id = status.get("id")
    desc = status.get("description") or ""

    passed: bool | None = None
    if expected_output is not None:
        passed = out == _norm_out(expected_output)

    return {
        "stdout": out,
        "stderr": err,
        "compile_output": comp,
        "time": time_val,
        "memory": mem,
        "status_id": status_id,
        "status_description": desc,
        "passed": passed,
        "raw": sub,
    }
