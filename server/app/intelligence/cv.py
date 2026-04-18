"""CV / resume fetching, parsing, and structuring.

Fetches a candidate's PDF from Supabase Storage, extracts text, and uses
the LLM to produce a short structured summary (skills, projects, experience)
used downstream to personalise interview questions and follow-ups.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("qace.cv")

# In-process cache: user_id -> (cv_hash, CVProfile)
_cv_cache: dict[str, tuple[str, "CVProfile"]] = {}


@dataclass
class CVProfile:
    raw_text: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    projects: list[dict[str, str]] = field(default_factory=list)  # {name, description, tech}
    experience: list[dict[str, str]] = field(default_factory=list)  # {role, company, highlights}
    cv_hash: str = ""

    def is_empty(self) -> bool:
        return not self.raw_text.strip()

    def to_prompt_summary(self, max_chars: int = 1200) -> str:
        """Compact plaintext summary to inject into LLM prompts."""
        if self.is_empty():
            return ""
        parts: list[str] = []
        if self.summary:
            parts.append(self.summary)
        if self.skills:
            parts.append("Skills: " + ", ".join(self.skills[:25]))
        if self.projects:
            proj_lines = []
            for p in self.projects[:5]:
                name = p.get("name", "").strip()
                desc = p.get("description", "").strip()
                tech = p.get("tech", "").strip()
                if not name and not desc:
                    continue
                line = f"- {name}" if name else "- Project"
                if tech:
                    line += f" ({tech})"
                if desc:
                    line += f": {desc}"
                proj_lines.append(line)
            if proj_lines:
                parts.append("Projects:\n" + "\n".join(proj_lines))
        if self.experience:
            exp_lines = []
            for e in self.experience[:4]:
                role = e.get("role", "").strip()
                company = e.get("company", "").strip()
                highlights = e.get("highlights", "").strip()
                if not role and not company:
                    continue
                line = f"- {role} at {company}" if role and company else f"- {role or company}"
                if highlights:
                    line += f": {highlights}"
                exp_lines.append(line)
            if exp_lines:
                parts.append("Experience:\n" + "\n".join(exp_lines))
        text = "\n\n".join(parts)
        return text[:max_chars]


async def _download_pdf(url: str, timeout_s: float = 15.0) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.get(url)
            if r.status_code != 200:
                logger.warning("CV download failed %s: %s", url, r.status_code)
                return None
            return r.content
    except Exception as exc:
        logger.warning("CV download error: %s", exc)
        return None


async def _fetch_user_metadata(base_url: str, service_key: str, user_id: str) -> dict[str, Any]:
    """Fetch auth.users raw_user_meta_data via Supabase admin API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{base_url.rstrip('/')}/auth/v1/admin/users/{user_id}",
                headers={
                    "apikey": service_key,
                    "Authorization": f"Bearer {service_key}",
                },
            )
            if r.status_code != 200:
                logger.warning("user meta fetch failed: %s %s", r.status_code, r.text[:200])
                return {}
            data = r.json()
            return data.get("user_metadata") or data.get("raw_user_meta_data") or {}
    except Exception as exc:
        logger.warning("user meta fetch error: %s", exc)
        return {}


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            logger.warning("Neither pypdf nor PyPDF2 installed — cannot parse CV")
            return ""
    try:
        import io
        reader = PdfReader(io.BytesIO(pdf_bytes))
        chunks = []
        for page in reader.pages:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(chunks)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception as exc:
        logger.warning("PDF parse failed: %s", exc)
        return ""


async def _structure_cv_with_llm(raw_text: str, settings: Any) -> dict[str, Any]:
    """Use the configured LLM to produce a compact structured CV JSON."""
    from .llm import call_llm, resolve_provider_config

    provider = resolve_provider_config(settings)
    if provider is None:
        return {}

    sys_prompt = (
        "You extract structured data from a candidate's CV. "
        "Return ONLY valid minified JSON, no prose. Schema: "
        '{"summary": str, "skills": [str], '
        '"projects": [{"name": str, "description": str, "tech": str}], '
        '"experience": [{"role": str, "company": str, "highlights": str}]}. '
        "Keep summary under 280 chars. Max 20 skills, 5 projects, 4 experiences. "
        "Highlights and descriptions should be one concise sentence each."
    )
    truncated = raw_text[:8000]

    try:
        raw = await call_llm(
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": truncated},
            ],
            provider,
            temperature=0.2,
            max_tokens=900,
            timeout_s=25.0,
        )
    except Exception as exc:
        logger.warning("CV LLM call failed: %s", exc)
        return {}

    if not raw:
        return {}

    # Strip code fences if model added them
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    # Try to find first {...} block
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(0)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        logger.warning("CV JSON parse failed: %s (raw: %s)", exc, cleaned[:200])
    return {}


async def fetch_and_parse_cv(
    user_id: str | None,
    settings: Any,
) -> CVProfile:
    """Fetch the user's CV from Supabase Storage and return a structured profile.

    Cached per user_id by PDF hash — re-parses only when the PDF changes.
    Returns an empty CVProfile if anything fails or the user has no CV.
    """
    if not user_id:
        return CVProfile()

    base_url = getattr(settings, "supabase_url", "") or ""
    service_key = getattr(settings, "supabase_service_role_key", "") or ""
    if not base_url or not service_key:
        logger.info("Supabase not configured — skipping CV fetch")
        return CVProfile()

    meta = await _fetch_user_metadata(base_url, service_key, user_id)
    cv_url = meta.get("cv_url")
    if not cv_url:
        logger.info("User %s has no CV uploaded", user_id[:8])
        return CVProfile()

    pdf_bytes = await _download_pdf(cv_url)
    if not pdf_bytes:
        return CVProfile()

    cv_hash = hashlib.sha256(pdf_bytes).hexdigest()

    cached = _cv_cache.get(user_id)
    if cached and cached[0] == cv_hash:
        logger.info("CV cache hit for user %s (hash %s)", user_id[:8], cv_hash[:8])
        return cached[1]

    raw_text = _extract_pdf_text(pdf_bytes)
    if not raw_text:
        empty = CVProfile(cv_hash=cv_hash)
        _cv_cache[user_id] = (cv_hash, empty)
        return empty

    structured = await _structure_cv_with_llm(raw_text, settings)
    profile = CVProfile(
        raw_text=raw_text,
        summary=str(structured.get("summary", ""))[:400],
        skills=[str(s)[:60] for s in (structured.get("skills") or []) if s][:25],
        projects=[
            {
                "name": str(p.get("name", ""))[:80],
                "description": str(p.get("description", ""))[:240],
                "tech": str(p.get("tech", ""))[:120],
            }
            for p in (structured.get("projects") or [])
            if isinstance(p, dict)
        ][:5],
        experience=[
            {
                "role": str(e.get("role", ""))[:80],
                "company": str(e.get("company", ""))[:80],
                "highlights": str(e.get("highlights", ""))[:240],
            }
            for e in (structured.get("experience") or [])
            if isinstance(e, dict)
        ][:4],
        cv_hash=cv_hash,
    )
    _cv_cache[user_id] = (cv_hash, profile)
    logger.info(
        "CV parsed for user %s: %d skills, %d projects, %d experiences",
        user_id[:8], len(profile.skills), len(profile.projects), len(profile.experience),
    )
    return profile


async def generate_cv_questions(
    cv: CVProfile,
    job_role: str,
    count: int,
    settings: Any,
) -> list[str]:
    """Generate interview questions grounded in the candidate's CV."""
    if cv.is_empty() or count <= 0:
        return []

    from .llm import call_llm, resolve_provider_config

    provider = resolve_provider_config(settings)
    if provider is None:
        return []

    sys_prompt = (
        f"You are an interviewer preparing for a {job_role.replace('_', ' ')} interview. "
        f"Using the candidate's CV, write {count} specific interview questions that "
        "reference their actual projects, skills, or experience (name projects, "
        "technologies, or roles explicitly). Each question should probe depth of "
        "understanding, trade-offs, or decisions. Return ONLY a JSON array of strings, no prose."
    )
    user_content = cv.to_prompt_summary()

    try:
        raw = await call_llm(
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content},
            ],
            provider,
            temperature=0.6,
            max_tokens=500,
            timeout_s=20.0,
        )
    except Exception as exc:
        logger.warning("CV question gen failed: %s", exc)
        return []
    if not raw:
        return []

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    m = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(0)
    try:
        arr = json.loads(cleaned)
        if isinstance(arr, list):
            return [str(q).strip() for q in arr if isinstance(q, (str, int, float)) and str(q).strip()][:count]
    except Exception as exc:
        logger.warning("CV questions JSON parse failed: %s", exc)
    return []
