"""
Q&Ace — Per-user personalization layer.

Builds a compact "Student Context Block" from existing Supabase data
(user_profiles, mcq_topic_progress, interview_sessions) for injection
into the system prompts of notes_chat and coaching.

Returns "" for guests (unauthenticated) so callers can fall back to
generic behavior unchanged.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import get_settings
from .intelligence.llm import call_llm, resolve_provider_config

logger = logging.getLogger("qace.personalization")

WEAK_SCORE_THRESHOLD = 60.0
STRONG_SCORE_THRESHOLD = 80.0
MAX_WEAK_TOPICS = 3
MAX_STRONG_TOPICS = 2


def _humanize_topic(topic_id: str) -> str:
    return topic_id.replace("-", " ").replace("_", " ").title() if topic_id else ""


def _first_name(full_name: str | None) -> str:
    if not full_name:
        return ""
    return full_name.strip().split()[0] if full_name.strip() else ""


def _weakest_dimension(content: float, delivery: float, composure: float) -> str:
    pairs = [("Content", content), ("Delivery", delivery), ("Composure", composure)]
    pairs.sort(key=lambda p: p[1])
    name, score = pairs[0]
    return f"{name} ({score:.0f})"


def _supabase_config() -> tuple[str, dict[str, str]] | None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    key = settings.supabase_service_role_key.strip()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    return settings.supabase_url.rstrip("/"), headers


async def _supabase_get(path: str, params: dict[str, str]) -> list[dict[str, Any]] | None:
    cfg = _supabase_config()
    if cfg is None:
        return None
    base, headers = cfg
    url = f"{base}/rest/v1/{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers=headers, params=params)
            if r.status_code != 200:
                logger.warning("Supabase GET %s -> %s %s", path, r.status_code, r.text[:200])
                return None
            return r.json()
    except Exception as exc:
        logger.warning("Supabase GET %s failed: %s", path, exc)
        return None


async def _supabase_post(
    path: str,
    body: list[dict[str, Any]] | dict[str, Any],
    *,
    prefer: str = "return=representation",
    params: dict[str, str] | None = None,
) -> list[dict[str, Any]] | None:
    cfg = _supabase_config()
    if cfg is None:
        return None
    base, headers = cfg
    headers = {**headers, "Prefer": prefer}
    url = f"{base}/rest/v1/{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, headers=headers, json=body, params=params or {})
            if r.status_code not in (200, 201):
                logger.warning("Supabase POST %s -> %s %s", path, r.status_code, r.text[:200])
                return None
            try:
                return r.json()
            except Exception:
                return []
    except Exception as exc:
        logger.warning("Supabase POST %s failed: %s", path, exc)
        return None


async def build_student_context(user_id: str | None) -> str:
    """
    Return a compact, prompt-ready paragraph describing the student.

    Empty string for guests or when Supabase is not configured — callers
    should fall back to generic behavior in that case.
    """
    if not user_id:
        return ""

    profile_rows = await _supabase_get(
        "user_profiles",
        {"id": f"eq.{user_id}", "select": "full_name", "limit": "1"},
    )
    progress_rows = await _supabase_get(
        "mcq_topic_progress",
        {
            "user_id": f"eq.{user_id}",
            "select": "topic_id,average_score,latest_score,attempts_count",
            "order": "attempts_count.desc",
            "limit": "20",
        },
    )
    session_rows = await _supabase_get(
        "interview_sessions",
        {
            "user_id": f"eq.{user_id}",
            "select": "mode,difficulty,final_score,content_score,delivery_score,composure_score,started_at",
            "order": "started_at.desc",
            "limit": "1",
        },
    )

    full_name = (profile_rows[0].get("full_name") if profile_rows else "") or ""
    name = _first_name(full_name)

    weak: list[str] = []
    strong: list[str] = []
    for row in (progress_rows or []):
        topic = _humanize_topic(str(row.get("topic_id", "")))
        avg = float(row.get("average_score") or 0)
        if not topic:
            continue
        if avg and avg < WEAK_SCORE_THRESHOLD and len(weak) < MAX_WEAK_TOPICS:
            weak.append(f"{topic} ({avg:.0f}%)")
        elif avg >= STRONG_SCORE_THRESHOLD and len(strong) < MAX_STRONG_TOPICS:
            strong.append(f"{topic} ({avg:.0f}%)")

    interview_line = ""
    if session_rows:
        s = session_rows[0]
        final = float(s.get("final_score") or 0)
        if final > 0:
            weakest = _weakest_dimension(
                float(s.get("content_score") or 0),
                float(s.get("delivery_score") or 0),
                float(s.get("composure_score") or 0),
            )
            interview_line = (
                f"- Last interview: {s.get('mode','technical')}/{s.get('difficulty','standard')}, "
                f"overall {final:.0f}/100; weakest dimension was {weakest}."
            )

    summary_row = await fetch_student_summary(user_id)

    if not (name or weak or strong or interview_line or summary_row):
        return ""

    lines = ["", "## About this student"]
    if name:
        lines.append(f"- Name: {name} (greet by first name on the first turn, never the full name)")
    if weak:
        lines.append(f"- Weak topics (avg < {WEAK_SCORE_THRESHOLD:.0f}%): {', '.join(weak)}")
    if strong:
        lines.append(f"- Strong topics: {', '.join(strong)}")
    if interview_line:
        lines.append(interview_line)
    if summary_row:
        s = (summary_row.get("summary") or "").strip()
        confusions = (summary_row.get("recurring_confusions") or "").strip()
        goals = (summary_row.get("goals") or "").strip()
        if s:
            lines.append(f"- Long-term notes: {s}")
        if confusions:
            lines.append(f"- Recurring confusions: {confusions}")
        if goals:
            lines.append(f"- Stated goals: {goals}")
    lines.append(
        "- Reference the above naturally only when relevant. Don't recite it back. "
        "Be a warm mentor: encouraging, honest about gaps, celebrate progress."
    )
    return "\n".join(lines)


# ── Persistent chat history (Phase B) ─────────────────────────────────────────


async def get_or_create_conversation(
    user_id: str,
    surface: str,
    *,
    topic_id: str | None = None,
    session_id: str | None = None,
) -> str | None:
    """
    Return the conversation id for (user, surface, topic|session). Creates one
    if it doesn't exist. Returns None if Supabase is unconfigured.
    """
    if surface not in {"notes_chat", "coaching"}:
        return None

    params: dict[str, str] = {
        "user_id": f"eq.{user_id}",
        "surface": f"eq.{surface}",
        "select": "id",
        "limit": "1",
    }
    if surface == "notes_chat":
        if not topic_id:
            return None
        params["topic_id"] = f"eq.{topic_id}"
    else:
        if not session_id:
            return None
        params["session_id"] = f"eq.{session_id}"

    rows = await _supabase_get("chat_conversations", params)
    if rows:
        return str(rows[0]["id"])

    body: dict[str, Any] = {"user_id": user_id, "surface": surface}
    if surface == "notes_chat":
        body["topic_id"] = topic_id
    else:
        body["session_id"] = session_id

    created = await _supabase_post("chat_conversations", body)
    if created:
        return str(created[0]["id"])
    return None


async def insert_message(conversation_id: str, role: str, content: str) -> None:
    if not content.strip():
        return
    if role not in {"user", "assistant"}:
        return
    await _supabase_post(
        "chat_messages",
        {"conversation_id": conversation_id, "role": role, "content": content},
        prefer="return=minimal",
    )


async def fetch_recent_messages(
    conversation_id: str,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Return the most recent N messages in chronological order."""
    rows = await _supabase_get(
        "chat_messages",
        {
            "conversation_id": f"eq.{conversation_id}",
            "select": "role,content,created_at",
            "order": "created_at.desc",
            "limit": str(limit),
        },
    )
    if not rows:
        return []
    rows.reverse()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


async def fetch_history_for_user(
    user_id: str,
    surface: str,
    *,
    topic_id: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, str]]:
    """
    Convenience for the GET history endpoint. Returns [] if there's no
    conversation yet.
    """
    cid = await get_or_create_conversation(
        user_id, surface, topic_id=topic_id, session_id=session_id
    )
    if not cid:
        return []
    return await fetch_recent_messages(cid, limit=limit)


# ── Rolling student summary (Phase C) ─────────────────────────────────────────


REFRESH_AFTER_N_NEW_MESSAGES = 10
SUMMARY_PROMPT = """\
You maintain a long-term mental model of a single student that a tutor uses \
across many conversations. Update the model based on the recent conversation \
and current scores.

Output STRICTLY this JSON schema, nothing else:
{
  "summary": "<= 180 words, third-person, capturing how this student learns, \
their style, what excites them, what they consistently struggle with, recent \
trajectory. Preserve important traits from the previous summary unless new \
evidence overrides them.",
  "recurring_confusions": "<= 60 words, comma-separated list of up to 3 \
specific topics or concepts they keep tripping on. Empty string if none yet.",
  "goals": "<= 60 words. Their stated goals if mentioned, else preserve the \
existing goals string."
}
"""


async def _supabase_upsert(path: str, body: dict[str, Any], on_conflict: str) -> bool:
    cfg = _supabase_config()
    if cfg is None:
        return False
    base, headers = cfg
    headers = {**headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
    url = f"{base}/rest/v1/{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                url, headers=headers, json=body, params={"on_conflict": on_conflict}
            )
            if r.status_code not in (200, 201, 204):
                logger.warning("Supabase upsert %s -> %s %s", path, r.status_code, r.text[:200])
                return False
            return True
    except Exception as exc:
        logger.warning("Supabase upsert %s failed: %s", path, exc)
        return False


async def fetch_student_summary(user_id: str) -> dict[str, Any] | None:
    rows = await _supabase_get(
        "student_summary",
        {
            "user_id": f"eq.{user_id}",
            "select": "summary,recurring_confusions,goals,message_count_at_last_refresh",
            "limit": "1",
        },
    )
    if not rows:
        return None
    return rows[0]


async def _count_user_messages(user_id: str) -> int:
    """Total user-authored chat_messages across all conversations for this user."""
    cfg = _supabase_config()
    if cfg is None:
        return 0
    base, headers = cfg
    # Use PostgREST count with a filter joining via conversation ownership.
    # Cheapest path: pull conversation ids for this user, then count messages.
    convo_rows = await _supabase_get(
        "chat_conversations",
        {"user_id": f"eq.{user_id}", "select": "id", "limit": "200"},
    )
    if not convo_rows:
        return 0
    ids = ",".join(str(r["id"]) for r in convo_rows)
    headers_with_count = {**headers, "Prefer": "count=exact"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.head(
                f"{base}/rest/v1/chat_messages",
                headers=headers_with_count,
                params={
                    "conversation_id": f"in.({ids})",
                    "role": "eq.user",
                },
            )
            cr = r.headers.get("content-range", "")
            if "/" in cr:
                total = cr.split("/")[-1]
                return int(total) if total.isdigit() else 0
    except Exception as exc:
        logger.warning("count user messages failed: %s", exc)
    return 0


def _parse_summary_json(raw: str) -> dict[str, str] | None:
    import json as _json
    if not raw:
        return None
    raw = raw.strip()
    # Try direct parse, then strip ```json fences.
    for candidate in (raw, raw.strip("`").lstrip("json").strip()):
        try:
            obj = _json.loads(candidate)
            if isinstance(obj, dict):
                return {
                    "summary": str(obj.get("summary", "") or "")[:1500],
                    "recurring_confusions": str(obj.get("recurring_confusions", "") or "")[:500],
                    "goals": str(obj.get("goals", "") or "")[:500],
                }
        except Exception:
            continue
    # Fallback: locate first {...} block.
    start = raw.find("{")
    end = raw.rfind("}")
    if 0 <= start < end:
        try:
            obj = _json.loads(raw[start : end + 1])
            if isinstance(obj, dict):
                return {
                    "summary": str(obj.get("summary", "") or "")[:1500],
                    "recurring_confusions": str(obj.get("recurring_confusions", "") or "")[:500],
                    "goals": str(obj.get("goals", "") or "")[:500],
                }
        except Exception:
            return None
    return None


async def maybe_refresh_summary(
    user_id: str,
    *,
    conversation_id: str | None = None,
    force: bool = False,
) -> bool:
    """
    Refresh the student_summary row if (force) or if the user has accumulated
    >= REFRESH_AFTER_N_NEW_MESSAGES new user-authored messages since the last
    refresh. Best-effort: never raises.
    """
    try:
        current = await fetch_student_summary(user_id)
        prev_summary = (current or {}).get("summary", "") or ""
        prev_goals = (current or {}).get("goals", "") or ""
        last_count = int((current or {}).get("message_count_at_last_refresh") or 0)

        total_user_msgs = await _count_user_messages(user_id)
        if not force and (total_user_msgs - last_count) < REFRESH_AFTER_N_NEW_MESSAGES:
            return False

        recent: list[dict[str, str]] = []
        if conversation_id:
            recent = await fetch_recent_messages(conversation_id, limit=20)

        recent_text = "\n".join(
            f"{m['role'].upper()}: {m['content'][:300]}" for m in recent
        ) or "(no recent conversation)"

        score_block = await build_student_context(user_id)

        user_msg = (
            f"Previous summary:\n{prev_summary or '(none yet)'}\n\n"
            f"Previous goals:\n{prev_goals or '(none recorded)'}\n\n"
            f"Recent conversation excerpts:\n{recent_text}\n\n"
            f"Latest scores and progress:\n{score_block or '(no progress data)'}"
        )

        provider = resolve_provider_config(get_settings())
        if provider is None:
            return False

        raw = await call_llm(
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            provider_config=provider,
            temperature=0.3,
            max_tokens=600,
            timeout_s=30.0,
        )
        if not raw:
            return False

        parsed = _parse_summary_json(raw)
        if not parsed:
            logger.warning("summary refresh: could not parse LLM JSON output")
            return False

        await _supabase_upsert(
            "student_summary",
            {
                "user_id": user_id,
                "summary": parsed["summary"],
                "recurring_confusions": parsed["recurring_confusions"],
                "goals": parsed["goals"] or prev_goals,
                "message_count_at_last_refresh": total_user_msgs,
            },
            on_conflict="user_id",
        )
        return True
    except Exception as exc:
        logger.warning("maybe_refresh_summary failed: %s", exc)
        return False
