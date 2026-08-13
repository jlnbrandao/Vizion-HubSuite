"""Unit tests for HttpFileProvider."""

from __future__ import annotations

import httpx
import pytest

from src.modules.integrations.providers.http_file_provider import HttpFileProvider


def _patch_client(monkeypatch: pytest.MonkeyPatch, handler) -> None:  # type: ignore[no-untyped-def]
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        kwargs.setdefault("follow_redirects", True)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_http_file_test_connection_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "HEAD"
        assert request.url.path == "/data/addresses.json"
        return httpx.Response(200, headers={"content-type": "application/json"})

    _patch_client(monkeypatch, handler)
    provider = HttpFileProvider()
    result = await provider.test_connection(
        configuration={
            "url": "https://files.example.com/data/addresses.json",
            "format": "json",
            "auth_type": "none",
        },
        secrets={},
    )
    assert result.success is True
    assert result.permission == "JSON"
    assert result.server == "files.example.com"


@pytest.mark.asyncio
async def test_http_file_missing_bearer() -> None:
    provider = HttpFileProvider()
    result = await provider.test_connection(
        configuration={
            "url": "https://files.example.com/a.csv",
            "format": "csv",
            "auth_type": "bearer",
        },
        secrets={},
    )
    assert result.success is False
    assert "bearer" in (result.error_detail or "").lower()


@pytest.mark.asyncio
async def test_http_file_sync_json_array(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer tok-1"
        return httpx.Response(
            200,
            json=[{"id": 1}, {"id": 2}, {"id": 3}],
        )

    _patch_client(monkeypatch, handler)
    provider = HttpFileProvider()
    result = await provider.sync(
        configuration={
            "url": "https://files.example.com/items.json",
            "format": "json",
            "auth_type": "bearer",
        },
        secrets={"bearer_token": "tok-1"},
    )
    assert result.success is True
    assert result.records_processed == 3
    assert "tok-1" not in result.message


@pytest.mark.asyncio
async def test_http_file_sync_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("X-API-Key") == "key-9"
        return httpx.Response(
            200,
            content=b"id;city\n1;SP\n2;RJ\n",
            headers={"content-type": "text/csv"},
        )

    _patch_client(monkeypatch, handler)
    provider = HttpFileProvider()
    result = await provider.sync(
        configuration={
            "url": "https://files.example.com/cities.csv",
            "format": "csv",
            "auth_type": "api_key",
            "api_key_header": "X-API-Key",
            "delimiter": ";",
            "encoding": "utf-8",
        },
        secrets={"api_key": "key-9"},
    )
    assert result.success is True
    assert result.records_processed == 2
    assert "CSV" in result.message
    assert "key-9" not in result.message


@pytest.mark.asyncio
async def test_http_file_head_fallback_to_get(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "HEAD":
            return httpx.Response(405)
        return httpx.Response(200, json={"items": []})

    _patch_client(monkeypatch, handler)
    provider = HttpFileProvider()
    result = await provider.test_connection(
        configuration={
            "url": "https://files.example.com/data.json",
            "format": "json",
            "auth_type": "none",
        },
        secrets={},
    )
    assert result.success is True
    assert calls == ["HEAD", "GET"]


@pytest.mark.asyncio
async def test_http_file_rejects_bad_scheme() -> None:
    provider = HttpFileProvider()
    result = await provider.test_connection(
        configuration={"url": "ftp://files.example.com/a.csv", "format": "csv"},
        secrets={},
    )
    assert result.success is False
    assert "http" in (result.error_detail or "").lower()
