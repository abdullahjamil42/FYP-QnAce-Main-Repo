#!/usr/bin/env python3
"""Apply docs/migrations/001_coding_round.sql using psql or psycopg.

Requires DATABASE_URL or SUPABASE_DB_URL (Postgres URI from Supabase Dashboard → Settings → Database).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SQL_FILE = REPO / "docs" / "migrations" / "001_coding_round.sql"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    # Later files override earlier (secrets often live in client/_env.local)
    for name in (".env", "client/.env.local", "client/_env.local", "server/.env"):
        p = REPO / name
        if p.is_file():
            load_dotenv(p, override=True)


def main() -> int:
    _load_dotenv()
    url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("SUPABASE_DB_URL")
        or os.environ.get("SUPABASE_DATABASE_URL")
        or ""
    ).strip()
    if not url:
        print(
            "Missing DATABASE_URL or SUPABASE_DB_URL.\n"
            "Add it to client/_env.local or client/.env.local (or repo .env), e.g.:\n"
            "  DATABASE_URL=postgresql://postgres.[ref]:[PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres\n"
            "(Supabase → Project Settings → Database → URI + your DB password.)\n",
            file=sys.stderr,
        )
        return 1

    if not SQL_FILE.is_file():
        print(f"Missing {SQL_FILE}", file=sys.stderr)
        return 1

    psql = subprocess.run(
        ["psql", url, "-v", "ON_ERROR_STOP=1", "-f", str(SQL_FILE)],
        cwd=str(REPO),
    )
    return psql.returncode


if __name__ == "__main__":
    raise SystemExit(main())
