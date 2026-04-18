"""
Q&Ace — Supabase JWT authentication dependency.

Usage:
    from .auth import require_user

    @router.post("/webrtc/offer")
    async def offer(req: OfferRequest, user_id: str = Depends(require_user)):
        ...

Set SUPABASE_JWT_SECRET in .env (find it in Supabase dashboard → Settings → API → JWT Secret).
Set QACE_REQUIRE_AUTH=true to enforce auth; false (default) allows unauthenticated access in dev.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("qace.auth")
_bearer = HTTPBearer(auto_error=False)


def _decode_jwt(token: str, secret: str) -> dict:
    try:
        import jwt  # PyJWT
        return jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )


async def require_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[str]:
    """
    FastAPI dependency — returns the Supabase user_id (sub) from Bearer JWT.
    If QACE_REQUIRE_AUTH=false (default in dev), allows unauthenticated access
    and returns None so the rest of the app can handle guests gracefully.
    """
    from .config import get_settings
    settings = get_settings()

    if not settings.require_auth:
        # Dev mode: auth optional, extract user_id if token present
        if creds and creds.credentials and settings.supabase_jwt_secret:
            try:
                payload = _decode_jwt(creds.credentials, settings.supabase_jwt_secret)
                return payload.get("sub")
            except HTTPException:
                pass
        return None

    # Prod mode: token required
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    if not settings.supabase_jwt_secret:
        logger.error("SUPABASE_JWT_SECRET not set but QACE_REQUIRE_AUTH=true")
        raise HTTPException(status_code=500, detail="Auth misconfigured on server")

    payload = _decode_jwt(creds.credentials, settings.supabase_jwt_secret)
    return payload.get("sub")
