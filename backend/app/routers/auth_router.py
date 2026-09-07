import secrets

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app import auth, oidc
from app.audit import record
from app.auth import SESSION_COOKIE_NAME, get_current_user
from app.config import get_settings
from fastapi import Depends

router = APIRouter(prefix="/auth", tags=["auth"])

_oidc_states: set[str] = set()


class DevLoginRequest(BaseModel):
    username: str
    password: str


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        secure=settings.oidc_enabled,  # secure cookies once served over https in prod
        max_age=settings.session_ttl_minutes * 60,
    )


@router.post("/dev-login")
def dev_login(payload: DevLoginRequest, response: Response):
    settings = get_settings()
    if not settings.dev_login_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user = auth.dev_login(payload.username, payload.password)
    if not user:
        record(payload.username, "login", {}, "denied", "bad credentials")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = auth.create_session_token(user)
    _set_session_cookie(response, token)
    record(user.email, "login", {"method": "dev"}, "ok")
    return {"email": user.email, "groups": user.groups}


@router.get("/oidc/login")
def oidc_login():
    settings = get_settings()
    if not settings.oidc_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    state = secrets.token_urlsafe(24)
    _oidc_states.add(state)
    return RedirectResponse(oidc.build_authorization_url(state))


@router.get("/callback")
def oidc_callback(code: str, state: str, response: Response):
    settings = get_settings()
    if not settings.oidc_enabled or state not in _oidc_states:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OIDC state")
    _oidc_states.discard(state)
    userinfo = oidc.exchange_code_for_userinfo(code)
    email = userinfo.get("email") or userinfo.get("sub")
    groups = oidc.userinfo_to_groups(userinfo)
    user = auth.CurrentUser(email=email, groups=groups)
    token = auth.create_session_token(user)
    redirect = RedirectResponse(settings.frontend_origin)
    _set_session_cookie(redirect, token)
    record(email, "login", {"method": "oidc"}, "ok")
    return redirect


@router.post("/logout")
def logout(response: Response, user: auth.CurrentUser = Depends(get_current_user)):
    response.delete_cookie(SESSION_COOKIE_NAME)
    record(user.email, "logout", {}, "ok")
    return {"ok": True}


@router.get("/me")
def me(user: auth.CurrentUser = Depends(get_current_user)):
    return {"email": user.email, "groups": user.groups}
