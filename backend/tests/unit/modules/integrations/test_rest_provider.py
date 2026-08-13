"""Unit tests for RestProvider (httpx MockTransport)."""

from __future__ import annotations

import httpx
import pytest

from src.modules.integrations.providers.rest_provider import RestProvider


def _patch_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        kwargs.setdefault("follow_redirects", True)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_rest_provider_test_connection_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/addresses"
        assert request.headers.get("Authorization") == "Bearer secret-token"
        return httpx.Response(200, json={"items": [{"id": 1}]})

    _patch_client(monkeypatch, httpx.MockTransport(handler))

    provider = RestProvider(max_retries=0)
    result = await provider.test_connection(
        configuration={
            "base_url": "https://api.example.com",
            "endpoint": "/v1/addresses",
            "http_method": "GET",
            "auth_type": "bearer",
            "timeout_ms": 5000,
        },
        secrets={"bearer_token": "secret-token"},
    )
    assert result.success is True
    assert result.server == "api.example.com"
    assert result.authentication == "bearer"
    assert result.duration_ms is not None


@pytest.mark.asyncio
async def test_rest_provider_test_connection_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(
        monkeypatch,
        httpx.MockTransport(lambda _request: httpx.Response(401, json={"error": "nope"})),
    )

    provider = RestProvider(max_retries=0)
    result = await provider.test_connection(
        configuration={
            "base_url": "https://api.example.com",
            "endpoint": "/",
            "auth_type": "api_key",
        },
        secrets={"api_key": "k"},
    )
    assert result.success is False
    assert result.error_detail == "HTTP 401"
    assert "secret" not in (result.error_detail or "").lower()


@pytest.mark.asyncio
async def test_rest_provider_sync_pagination_offset(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        offset = int(request.url.params.get("offset", "0"))
        if offset == 0:
            return httpx.Response(200, json={"items": [{"id": i} for i in range(100)]})
        return httpx.Response(200, json={"items": [{"id": 100}]})

    _patch_client(monkeypatch, httpx.MockTransport(handler))

    provider = RestProvider(max_retries=0, max_pages=5)
    result = await provider.sync(
        configuration={
            "base_url": "https://api.example.com",
            "endpoint": "/items",
            "pagination": "offset",
            "rate_limit_per_minute": 6000,
        },
        secrets={},
    )
    assert result.success is True
    assert result.records_processed == 101
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_rest_provider_retries_on_503(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(503, json={"error": "busy"})
        return httpx.Response(200, json={"ok": True})

    _patch_client(monkeypatch, httpx.MockTransport(handler))

    provider = RestProvider(max_retries=3, retry_backoff_seconds=0.01)
    result = await provider.test_connection(
        configuration={"base_url": "https://api.example.com", "endpoint": "/"},
        secrets={},
    )
    assert result.success is True
    assert attempts["n"] == 3
