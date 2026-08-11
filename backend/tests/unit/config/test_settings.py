"""Settings validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.config.settings import Settings


def test_development_allows_weak_jwt_secret() -> None:
    settings = Settings(app_env="development", jwt_secret_key="change-me-in-production")
    assert settings.jwt_secret_key == "change-me-in-production"


def test_production_rejects_weak_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(app_env="production", jwt_secret_key="change-me-in-production")


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(app_env="production", jwt_secret_key="short-secret")


def test_production_rejects_empty_base_domains() -> None:
    with pytest.raises(ValidationError, match="ALLOWED_TENANT_BASE_DOMAINS"):
        Settings(
            app_env="production",
            jwt_secret_key="a" * 32,
            allowed_tenant_base_domains="",
            database_url="postgresql+asyncpg://app:s3cret@localhost:5432/lanstar",
            database_migrate_url="postgresql+asyncpg://mig:s3cret@localhost:5432/lanstar",
        )


def test_production_rejects_default_db_passwords() -> None:
    with pytest.raises(ValidationError, match="database credentials"):
        Settings(
            app_env="production",
            jwt_secret_key="a" * 32,
            allowed_tenant_base_domains="lanstar.com.br",
            database_url="postgresql+asyncpg://lanstar_app:lanstar_app@localhost:5432/lanstar",
        )


def test_production_accepts_strong_jwt_secret() -> None:
    secret = "a" * 32
    settings = Settings(
        app_env="production",
        jwt_secret_key=secret,
        allowed_tenant_base_domains="lanstar.com.br",
        database_url="postgresql+asyncpg://app:s3cret@localhost:5432/lanstar",
        database_migrate_url="postgresql+asyncpg://mig:s3cret@localhost:5432/lanstar",
    )
    assert settings.jwt_secret_key == secret
    assert settings.tenant_base_domains == ("lanstar.com.br",)
