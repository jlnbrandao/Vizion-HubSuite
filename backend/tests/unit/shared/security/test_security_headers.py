"""Security header middleware behaviour."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.config.settings import Settings
from src.shared.infrastructure.security.security_headers_middleware import (
    SecurityHeadersMiddleware,
)


def _app(settings: Settings) -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)

    @app.get("/api/v1/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    return app


async def _get(settings: Settings, path: str = "/api/v1/ping", **kwargs: object):
    transport = ASGITransport(app=_app(settings))
    async with AsyncClient(transport=transport, base_url="https://universe.lanstar.test") as client:
        return await client.get(path, **kwargs)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_baseline_headers_are_applied() -> None:
    response = await _get(Settings(app_env="development"))

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


@pytest.mark.asyncio
async def test_hsts_absent_in_development_present_when_enabled() -> None:
    dev = await _get(Settings(app_env="development"))
    assert "Strict-Transport-Security" not in dev.headers

    prod = await _get(Settings(app_env="development", hsts_enabled=True))
    hsts = prod.headers["Strict-Transport-Security"]
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts
    assert "preload" not in hsts


@pytest.mark.asyncio
async def test_credentialed_responses_are_not_cacheable() -> None:
    response = await _get(
        Settings(app_env="development"),
        headers={"Authorization": "Bearer token"},
    )
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.asyncio
async def test_headers_can_be_disabled() -> None:
    response = await _get(Settings(app_env="development", security_headers_enabled=False))
    assert "X-Frame-Options" not in response.headers
