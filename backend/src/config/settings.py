"""Application settings loaded from environment / .env file.

Centralizes configuration so modules never hardcode secrets or connection strings.
"""

from functools import lru_cache
from typing import Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_WEAK_JWT_SECRETS = frozenset(
    {
        "change-me-in-production",
        "change-me-in-production-use-long-random-string",
    }
)
_MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Lanstar"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "postgresql+asyncpg://lanstar:lanstar@localhost:5432/lanstar"
    # Alembic / seed (BYPASSRLS). Falls back to database_url when empty.
    database_migrate_url: str = ""
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Refresh cookie Secure flag. None = Secure outside development.
    # Set COOKIE_SECURE=false for HTTP-only deploys until TLS is enabled.
    cookie_secure: bool | None = None

    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    auth_rate_limit_requests: int = 20
    auth_rate_limit_window_seconds: int = 60

    # Allow demo seed password outside development (default: refuse).
    seed_allow_insecure: bool = False

    # Comma-separated base domains for Host validation (empty = any suffix in development).
    # Examples: "localhost,lanstar.com.br,lanstar.local"
    # IP form universe.134.x.x.x is always allowed (base is an IPv4).
    allowed_tenant_base_domains: str = "localhost,lanstar.com.br,lanstar.local"

    # IAM platform feature flags
    iam_oidc_enabled: bool = True
    iam_mfa_enabled: bool = True
    iam_mfa_required_roles: str = "ADMIN,PLATFORM"
    iam_scim_enabled: bool = True
    iam_federation_enabled: bool = True
    iam_abac_enabled: bool = True

    # SMTP for invitations / password reset (optional in development — tokens logged)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@lanstar.local"
    smtp_use_tls: bool = True

    # OIDC Authorization Server (RS256). Empty private key → ephemeral key in development.
    oidc_issuer_template: str = "https://{tenant_slug}.{base_domain}"
    oidc_jwt_private_key_pem: str = ""
    oidc_jwt_public_key_pem: str = ""
    mfa_token_expire_minutes: int = 5
    invitation_expire_hours: int = 72
    password_reset_expire_hours: int = 1

    # Fernet key material for integration secrets (falls back to JWT_SECRET_KEY).
    integration_secrets_key: str = ""

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def refresh_cookie_secure(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return not self.is_development

    @property
    def migrate_database_url(self) -> str:
        return self.database_migrate_url.strip() or self.database_url

    @property
    def tenant_base_domains(self) -> tuple[str, ...]:
        return tuple(
            part.strip().lower()
            for part in self.allowed_tenant_base_domains.split(",")
            if part.strip()
        )

    @property
    def mfa_required_role_names(self) -> frozenset[str]:
        return frozenset(
            part.strip().upper()
            for part in self.iam_mfa_required_roles.split(",")
            if part.strip()
        )

    @field_validator("allowed_tenant_base_domains", mode="before")
    @classmethod
    def _coerce_domains(cls, value: object) -> object:
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return ",".join(str(item) for item in value)
        return value

    @model_validator(mode="after")
    def _require_strong_jwt_secret(self) -> Self:
        if self.is_development:
            return self
        secret = self.jwt_secret_key.strip()
        if len(secret) < _MIN_JWT_SECRET_LENGTH or secret in _WEAK_JWT_SECRETS:
            raise ValueError(
                "JWT_SECRET_KEY must be a strong secret of at least "
                f"{_MIN_JWT_SECRET_LENGTH} characters when APP_ENV is not development"
            )
        if not self.tenant_base_domains:
            raise ValueError(
                "ALLOWED_TENANT_BASE_DOMAINS must be set when APP_ENV is not development"
            )
        weak_db_markers = (
            "://lanstar:lanstar@",
            "://lanstar_app:lanstar_app@",
            "://lanstar_migrate:lanstar_migrate@",
        )
        urls = (self.database_url, self.migrate_database_url)
        if any(marker in url for url in urls for marker in weak_db_markers):
            raise ValueError(
                "Default database credentials are not allowed when APP_ENV is not "
                "development — rotate lanstar / lanstar_app / lanstar_migrate passwords"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
