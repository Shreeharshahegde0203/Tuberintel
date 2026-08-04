from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Any

import httpx
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings


settings = get_settings()
bearer = HTTPBearer(auto_error=False)
_rate_limit_state: dict[str, tuple[float, int]] = {}


@dataclass
class AuthenticatedUser:
    id: str
    email: str | None
    role: str | None = None

    @property
    def is_admin(self) -> bool:
        if self.role == "admin":
            return True
        if self.id in settings.admin_user_id_list:
            return True
        return bool(self.email and self.email.lower() in settings.admin_email_list)


def _parse_test_token(token: str) -> AuthenticatedUser | None:
    if settings.environment != "test" or not token.startswith("test-token:"):
        return None
    _, user_id, email, role = (token.split(":", 3) + ["", "", "", ""])[:4]
    if not user_id:
        return None
    return AuthenticatedUser(id=user_id, email=email or None, role=role or None)


def _verify_supabase_token(token: str) -> AuthenticatedUser:
    test_user = _parse_test_token(token)
    if test_user:
        return test_user
    if not settings.supabase_url:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is not configured.")
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    try:
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            response = client.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
            if response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token.")
            payload = response.json()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Authentication verification failed.") from exc
    role = payload.get("role")
    if not role:
        app_metadata = payload.get("app_metadata") or {}
        role = app_metadata.get("role")
        if not role and isinstance(app_metadata.get("roles"), list) and "admin" in app_metadata["roles"]:
            role = "admin"
    return AuthenticatedUser(
        id=str(payload.get("id") or ""),
        email=payload.get("email"),
        role=role,
    )


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AuthenticatedUser | None:
    if not credentials:
        return None
    return _verify_supabase_token(credentials.credentials)


def require_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AuthenticatedUser:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    return _verify_supabase_token(credentials.credentials)


def require_admin_user(
    user: AuthenticatedUser | None = Depends(get_optional_current_user),
    x_internal_service_key: str | None = Header(default=None),
) -> AuthenticatedUser:
    if settings.internal_service_key and x_internal_service_key == settings.internal_service_key:
        return AuthenticatedUser(id="internal-service", email=None, role="admin")
    if not user or not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access is required.")
    return user


def enforce_rate_limit(key: str, *, limit: int = 5, window_seconds: int = 60) -> None:
    now = monotonic()
    window_start, count = _rate_limit_state.get(key, (now, 0))
    if now - window_start >= window_seconds:
        window_start, count = now, 0
    count += 1
    _rate_limit_state[key] = (window_start, count)
    if count > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded.")
