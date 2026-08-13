"""Unit tests for OAuth2Provider (Client Credentials)."""

from __future__ import annotations

import httpx
import pytest

from src.modules.integrations.providers.oauth2_provider import OAuth2Provider


def _patch_client(monkeypatch: pytest.MonkeyPatch, handler) -> None:  # type: ignore[no-untyped-def]
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        kwargs.setdefault("follow_redirects", True)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_oauth2_test_connection_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method}:{request.url.path}")
        if request.url.path == "/oauth/token":
            body = request.content.decode()
            assert "grant_type=client_credentials" in body
            assert "client_id=my-client" in body
            assert "client_secret=super-secret" in body
            assert "scope=addresses%3Aread" in body or "scope=addresses:read" in body
            return httpx.Response(
                200,
                json={
                    "access_token": "tok-abc",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        assert request.headers.get("Authorization") == "Bearer tok-abc"
        assert "tok-abc" not in str(request.url)
        return httpx.Response(200, json={"items": []})

    _patch_client(monkeypatch, handler)
    provider = OAuth2Provider()
    result = await provider.test_connection(
        configuration={
            "token_url": "https://auth.example.com/oauth/token",
            "client_id": "my-client",
            "scope": "addresses:read",
            "grant_type": "client_credentials",
            "endpoint": "https://api.example.com/v1/addresses",
        },
        secrets={"client_secret": "super-secret"},
    )
    assert result.success is True
    assert result.authentication == "OAuth 2.0"
    assert result.permission == "addresses:read"
    assert result.error_detail is None
    assert "tok-abc" not in (result.message or "")
    assert "super-secret" not in (result.message or "")
    assert calls[0].startswith("POST:")
    assert any(c.startswith("GET:") for c in calls)


@pytest.mark.asyncio
async def test_oauth2_missing_secret() -> None:
    provider = OAuth2Provider()
    result = await provider.test_connection(
        configuration={
            "token_url": "https://auth.example.com/oauth/token",
            "client_id": "my-client",
            "endpoint": "https://api.example.com/v1/addresses",
        },
        secrets={},
    )
    assert result.success is False
    assert "secret" in (result.error_detail or "").lower()


@pytest.mark.asyncio
async def test_oauth2_token_cache_reuses_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token_calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/token":
            token_calls["n"] += 1
            return httpx.Response(
                200,
                json={
                    "access_token": "cached-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        return httpx.Response(200, json={"ok": True})

    _patch_client(monkeypatch, handler)
    provider = OAuth2Provider()
    config = {
        "token_url": "https://auth.example.com/oauth/token",
        "client_id": "my-client",
        "scope": "read",
        "endpoint": "https://api.example.com/resource",
    }
    secrets = {"client_secret": "s"}

    t1 = await provider.get_access_token(configuration=config, secrets=secrets)
    t2 = await provider.get_access_token(configuration=config, secrets=secrets)
    assert t1 == t2 == "cached-token"
    assert token_calls["n"] == 1

    t3 = await provider.get_access_token(
        configuration=config, secrets=secrets, force_refresh=True
    )
    assert t3 == "cached-token"
    assert token_calls["n"] == 2


@pytest.mark.asyncio
async def test_oauth2_token_endpoint_401(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(
        monkeypatch,
        lambda _r: httpx.Response(401, json={"error": "invalid_client"}),
    )
    provider = OAuth2Provider()
    result = await provider.test_connection(
        configuration={
            "token_url": "https://auth.example.com/oauth/token",
            "client_id": "bad",
            "endpoint": "https://api.example.com/v1/x",
        },
        secrets={"client_secret": "bad"},
    )
    assert result.success is False
    assert "401" in (result.error_detail or "")
    assert "bad" not in (result.error_detail or "")
