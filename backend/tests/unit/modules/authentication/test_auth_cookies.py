"""Refresh cookie helpers also set a readable session hint for the SPA."""

from __future__ import annotations

from starlette.responses import Response

from src.config.settings import Settings
from src.modules.authentication.routes.auth_cookies import (
    HOST_REFRESH_COOKIE_NAME,
    LEGACY_REFRESH_COOKIE_NAME,
    SESSION_HINT_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)


def _settings() -> Settings:
    return Settings(
        jwt_secret_key="test-secret-key-for-unit-tests-32b",
        app_env="development",
    )


def test_login_sets_http_only_refresh_and_readable_hint() -> None:
    response = Response()
    set_refresh_cookie(response, "opaque-refresh-token-value", _settings())
    headers = [value.lower() for value in response.headers.getlist("set-cookie")]

    refresh = next(h for h in headers if LEGACY_REFRESH_COOKIE_NAME in h)
    hint = next(h for h in headers if SESSION_HINT_COOKIE_NAME in h)

    assert "httponly" in refresh
    assert "httponly" not in hint
    assert "vizion_has_session=1" in hint


def test_logout_clears_refresh_and_session_hint() -> None:
    response = Response()
    clear_refresh_cookie(response, _settings())
    headers = " ".join(response.headers.getlist("set-cookie")).lower()

    assert LEGACY_REFRESH_COOKIE_NAME in headers
    assert SESSION_HINT_COOKIE_NAME in headers
    assert "max-age=0" in headers
    # `__Host-` on HTTP is rejected by the browser ("invalid prefix").
    assert HOST_REFRESH_COOKIE_NAME.lower() not in headers


def test_secure_logout_clears_host_prefixed_cookie() -> None:
    settings = Settings(
        jwt_secret_key="test-secret-key-for-unit-tests-32b",
        app_env="development",
        cookie_secure=True,
    )
    response = Response()
    clear_refresh_cookie(response, settings)
    headers = [value.lower() for value in response.headers.getlist("set-cookie")]

    host = next(h for h in headers if HOST_REFRESH_COOKIE_NAME.lower() in h)
    assert "secure" in host
    assert "max-age=0" in host
