"""JWT session handling + dev-login + OIDC (AWS SSO / IAM Identity Center) login."""
import time
from dataclasses import dataclass

from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_COOKIE_NAME = "eksdash_session"


@dataclass
class CurrentUser:
    email: str
    groups: list[str]


def _parse_dev_users() -> dict[str, tuple[str, str]]:
    """DEV_USERS="user:pass:group,user2:pass2:group2" -> {user: (pass, group)}"""
    settings = get_settings()
    users = {}
    for entry in settings.dev_users.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":")
        if len(parts) != 3:
            continue
        username, password, group = parts
        users[username] = (password, group)
    return users


def dev_login(username: str, password: str) -> CurrentUser | None:
    settings = get_settings()
    if not settings.dev_login_enabled:
        return None
    users = _parse_dev_users()
    entry = users.get(username)
    if not entry:
        return None
    expected_password, group = entry
    # Plain comparison is acceptable here only because this is an explicitly
    # opt-in local-development fallback (DEV_LOGIN_ENABLED), never for production.
    if password != expected_password:
        return None
    return CurrentUser(email=username, groups=[group])


def create_session_token(user: CurrentUser) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": user.email,
        "groups": user.groups,
        "iat": now,
        "exp": now + settings.session_ttl_minutes * 60,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_session_token(token: str) -> CurrentUser:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc
    return CurrentUser(email=payload["sub"], groups=payload.get("groups", []))


def get_current_user(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> CurrentUser:
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return decode_session_token(session)
