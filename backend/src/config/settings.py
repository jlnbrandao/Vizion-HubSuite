"""Application settings loaded from environment / .env file.

Centralizes configuration so modules never hardcode secrets or connection strings.
"""

from functools import lru_cache
from typing import Self

from pydantic import model_validator
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
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

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
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
