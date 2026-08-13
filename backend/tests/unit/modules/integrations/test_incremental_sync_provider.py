"""Unit tests for IncrementalSyncProvider."""

from __future__ import annotations

import httpx
import pytest

from src.modules.integrations.providers.incremental_sync_provider import (
    IncrementalSyncProvider,
)


def _patch_client(monkeypatch: pytest.MonkeyPatch, handler) -> None:  # type: ignore[no-untyped-def]
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        kwargs.setdefault("follow_redirects", True)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_incremental_test_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("page_size") == "50"
        assert request.url.params.get("updated_since") == "2026-01-01T00:00:00Z"
        return httpx.Response(200, json={"items": []})

    _patch_client(monkeypatch, handler)
    provider = IncrementalSyncProvider()
    result = await provider.test_connection(
        configuration={
            "base_url": "https://api.example.com",
            "endpoint": "/v1/addresses",
            "cursor_field": "updated_since",
            "cursor_value": "2026-01-01T00:00:00Z",
            "page_size": 50,
            "auth_type": "none",
        },
        secrets={},
    )
    assert result.success is True
    assert "updated_since" in (result.permission or "")


@pytest.mark.asyncio
async def test_incremental_sync_advances_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        cursor = request.url.params.get("updated_since")
        calls.append(cursor)
        if cursor is None:
            return httpx.Response(
                200,
                json={
                    "items": [
                        {"id": "1", "updated_at": "2026-02-01T00:00:00Z"},
                        {"id": "2", "updated_at": "2026-02-02T00:00:00Z"},
                    ],
                    "next_cursor": "2026-02-02T00:00:00Z",
                },
            )
        if cursor == "2026-02-02T00:00:00Z":
            return httpx.Response(
                200,
                json={
                    "items": [{"id": "3", "updated_at": "2026-02-03T00:00:00Z"}],
                    "next_cursor": "2026-02-03T00:00:00Z",
                },
            )
        return httpx.Response(200, json={"items": []})

    _patch_client(monkeypatch, handler)
    provider = IncrementalSyncProvider()
    result = await provider.sync(
        configuration={
            "base_url": "https://api.example.com",
            "endpoint": "/v1/addresses",
            "cursor_field": "updated_since",
            "page_size": 2,
            "auth_type": "none",
        },
        secrets={},
    )
    assert result.success is True
    assert result.mode == "incremental"
    assert result.records_processed == 3
    assert result.cursor_value == "2026-02-03T00:00:00Z"
    assert calls[0] is None
    assert "2026-02-02T00:00:00Z" in calls


@pytest.mark.asyncio
async def test_incremental_sync_uses_item_watermark(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": "a", "updated_since": "2026-03-01T10:00:00Z"},
                    {"id": "b", "updated_since": "2026-03-01T12:00:00Z"},
                ]
            },
        )

    _patch_client(monkeypatch, handler)
    provider = IncrementalSyncProvider()
    result = await provider.sync(
        configuration={
            "base_url": "https://api.example.com",
            "endpoint": "/items",
            "cursor_field": "updated_since",
            "page_size": 100,
        },
        secrets={},
    )
    assert result.success is True
    assert result.records_processed == 2
    assert result.cursor_value == "2026-03-01T12:00:00Z"


@pytest.mark.asyncio
async def test_incremental_missing_bearer() -> None:
    provider = IncrementalSyncProvider()
    result = await provider.test_connection(
        configuration={
            "base_url": "https://api.example.com",
            "endpoint": "/",
            "auth_type": "bearer",
        },
        secrets={},
    )
    assert result.success is False
    assert "bearer" in (result.error_detail or "").lower()
