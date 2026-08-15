"""Every response carries a correlation id, and an inbound one is preserved."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.shared.infrastructure.request_context import REQUEST_ID_HEADER, get_request_id
from src.shared.infrastructure.request_id_middleware import RequestIdMiddleware


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/echo")
    async def echo() -> dict[str, str | None]:
        return {"seen": get_request_id()}

    return app


@pytest.mark.asyncio
async def test_request_id_is_generated_when_absent() -> None:
    transport = ASGITransport(app=_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/echo")

    request_id = response.headers[REQUEST_ID_HEADER]
    assert request_id
    assert response.json()["seen"] == request_id


@pytest.mark.asyncio
async def test_inbound_request_id_is_reused() -> None:
    transport = ASGITransport(app=_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/echo", headers={REQUEST_ID_HEADER: "abc-123"})

    assert response.headers[REQUEST_ID_HEADER] == "abc-123"
    assert response.json()["seen"] == "abc-123"


@pytest.mark.asyncio
async def test_context_does_not_leak_between_requests() -> None:
    transport = ASGITransport(app=_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/echo", headers={REQUEST_ID_HEADER: "first"})
        second = await client.get("/echo")

    assert first.json()["seen"] == "first"
    assert second.json()["seen"] != "first"
