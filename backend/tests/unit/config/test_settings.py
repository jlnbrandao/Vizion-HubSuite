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


def test_production_accepts_strong_jwt_secret() -> None:
    secret = "a" * 32
    settings = Settings(app_env="production", jwt_secret_key=secret)
    assert settings.jwt_secret_key == secret
