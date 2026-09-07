from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env next to this package, not relative to the process's cwd.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    # AWS / EKS
    aws_region: str = "us-east-1"
    eks_cluster_name: str = "my-cluster"
    kubeconfig_path: str = "./generated-kubeconfig.yaml"

    # Session / JWT
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    session_ttl_minutes: int = 480

    # Frontend
    frontend_origin: str = "http://localhost:5173"

    # OIDC / AWS SSO
    oidc_enabled: bool = False
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Dev login fallback: "user:pass:group,user2:pass2:group2"
    dev_login_enabled: bool = True
    dev_users: str = "admin:admin123:admins"

    # RBAC
    rbac_mapping_file: str = "./rbac_mapping.yaml"

    # Audit
    audit_log_file: str = "./audit.log"


@lru_cache
def get_settings() -> Settings:
    return Settings()
