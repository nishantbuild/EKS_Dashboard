"""Generic OIDC login (works with AWS IAM Identity Center / Okta / Azure AD / Cognito).

Uses the standard Authorization Code flow. Point OIDC_ISSUER at your provider's
discovery-enabled base URL and register OIDC_CLIENT_ID/SECRET + OIDC_REDIRECT_URI
as an OAuth application there.
"""
from authlib.integrations.httpx_client import OAuth2Client

from app.config import get_settings

_SCOPE = "openid profile email"


def build_authorization_url(state: str) -> str:
    settings = get_settings()
    client = OAuth2Client(
        client_id=settings.oidc_client_id,
        redirect_uri=settings.oidc_redirect_uri,
        scope=_SCOPE,
    )
    url, _ = client.create_authorization_url(
        f"{settings.oidc_issuer.rstrip('/')}/authorize", state=state
    )
    return url


def exchange_code_for_userinfo(code: str) -> dict:
    settings = get_settings()
    client = OAuth2Client(
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        redirect_uri=settings.oidc_redirect_uri,
    )
    token = client.fetch_token(
        f"{settings.oidc_issuer.rstrip('/')}/token",
        code=code,
        grant_type="authorization_code",
    )
    resp = client.get(f"{settings.oidc_issuer.rstrip('/')}/userinfo", token=token)
    resp.raise_for_status()
    return resp.json()


def userinfo_to_groups(userinfo: dict) -> list[str]:
    groups = userinfo.get("groups") or userinfo.get("cognito:groups") or []
    if isinstance(groups, str):
        groups = [groups]
    return list(groups)
