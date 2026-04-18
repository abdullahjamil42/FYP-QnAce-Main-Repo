"""Fetch problems and test cases from Supabase REST (service role)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("qace.coding.supabase")


async def _get(
    base_url: str,
    headers: dict[str, str],
    path: str,
    params: dict[str, str],
) -> list[dict[str, Any]] | None:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(f"{base_url.rstrip('/')}/rest/v1/{path}", headers=headers, params=params)
            if r.status_code != 200:
                logger.warning("Supabase GET %s failed: %s %s", path, r.status_code, r.text[:200])
                return None
            return r.json()
    except Exception as exc:
        logger.warning("Supabase request failed: %s", exc)
        return None


def rest_headers(service_key: str, supabase_anon: str = "") -> dict[str, str]:
    key = service_key.strip()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def fetch_problem_row(base_url: str, service_key: str, problem_id: str) -> dict[str, Any] | None:
    rows = await _get(
        base_url,
        rest_headers(service_key),
        "problems",
        {"id": f"eq.{problem_id}", "select": "*"},
    )
    if not rows:
        return None
    return rows[0]


async def fetch_problem_public(base_url: str, service_key: str, problem_id: str) -> dict[str, Any] | None:
    """Problem fields for frontend (no test cases)."""
    return await fetch_problem_row(base_url, service_key, problem_id)


async def fetch_test_cases(
    base_url: str,
    service_key: str,
    problem_id: str,
    *,
    hidden: bool | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, str] = {
        "problem_id": f"eq.{problem_id}",
        "select": "id,stdin,expected_output,is_hidden,sort_order",
        "order": "sort_order.asc",
    }
    if hidden is not None:
        params["is_hidden"] = f"eq.{str(hidden).lower()}"
    rows = await _get(base_url, rest_headers(service_key), "test_cases", params)
    return rows or []


async def fetch_problems_list(
    base_url: str,
    service_key: str,
    *,
    difficulty: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return a list of available problems (id, title, difficulty, category)."""
    params: dict[str, str] = {
        "select": "id,title,difficulty,category",
        "order": "difficulty.asc,title.asc",
        "limit": str(limit),
    }
    if difficulty:
        params["difficulty"] = f"eq.{difficulty}"
    rows = await _get(base_url, rest_headers(service_key), "problems", params)
    return rows or []


async def patch_interview_session_coding_round(
    base_url: str,
    service_key: str,
    *,
    webrtc_session_id: str,
    coding_round: dict[str, Any],
) -> bool:
    """PATCH interview_sessions row by webrtc_session_id."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.patch(
                f"{base_url.rstrip('/')}/rest/v1/interview_sessions",
                headers=rest_headers(service_key),
                params={"webrtc_session_id": f"eq.{webrtc_session_id}"},
                json={"coding_round": coding_round},
            )
            if r.status_code not in (200, 204):
                logger.warning("PATCH interview_sessions failed: %s %s", r.status_code, r.text[:300])
                return False
            return True
    except Exception as exc:
        logger.warning("PATCH interview_sessions exception: %s", exc)
        return False
