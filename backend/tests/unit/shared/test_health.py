"""Smoke test for FastAPI health endpoint (no DB required)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app
from src.shared.infrastructure.di.container import create_container


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    container = create_container()
    app = create_app(container)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "app" in body
