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
            database_url="postgresql+asyncpg://app:s3cret@localhost:5432/vizion",
            database_migrate_url="postgresql+asyncpg://mig:s3cret@localhost:5432/vizion",
        )


def test_production_rejects_default_db_passwords() -> None:
    with pytest.raises(ValidationError, match="database credentials"):
        Settings(
            app_env="production",
            jwt_secret_key="a" * 32,
            allowed_tenant_base_domains="openvizion.com",
            database_url="postgresql+asyncpg://vizion_app:vizion_app@localhost:5432/vizion",
        )


def test_production_accepts_strong_jwt_secret() -> None:
    secret = "a" * 32
    settings = Settings(
        app_env="production",
        jwt_secret_key=secret,
        allowed_tenant_base_domains="openvizion.com",
        database_url="postgresql+asyncpg://app:s3cret@localhost:5432/vizion",
        database_migrate_url="postgresql+asyncpg://mig:s3cret@localhost:5432/vizion",
    )
    assert settings.jwt_secret_key == secret
    assert settings.tenant_base_domains == ("openvizion.com",)


def test_slug_aliases_parse() -> None:
    settings = Settings(tenant_slug_aliases="lanstar:universe, Foo:BAR")
    assert settings.slug_aliases == {"lanstar": "universe", "foo": "bar"}
