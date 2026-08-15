"""Login → me → refresh → logout over HTTP, including immediate revocation."""

from __future__ import annotations

from httpx import AsyncClient

from typing import Any

from src.shared.infrastructure.request_context import REQUEST_ID_HEADER
from tests.integration.conftest import TEST_USER_PASSWORD, auth, provisioned_user


async def test_login_returns_access_token_and_sets_refresh_cookie(
    app: Any, client: AsyncClient
) -> None:
    async with provisioned_user(
        app, tenant_slug="universe", role_name="VIEWER", username="itest_login"
    ) as email:
        response = await client.post(
            "/api/v1/auth/login", json={"login": email, "password": TEST_USER_PASSWORD}
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    # The refresh token never reaches JavaScript.
    assert not body.get("refresh_token")
    assert any("refresh" in name.lower() for name in response.cookies.keys())
    assert response.cookies.get("vizion_has_session") == "1"


async def test_login_is_rejected_with_a_wrong_password(
    app: Any, client: AsyncClient
) -> None:
    async with provisioned_user(
        app, tenant_slug="universe", role_name="VIEWER", username="itest_badpass"
    ) as email:
        response = await client.post(
            "/api/v1/auth/login", json={"login": email, "password": "Wrong-Password1!"}
        )

    assert response.status_code == 401


async def test_me_returns_identity_permissions_and_services(
    client: AsyncClient, admin_token: str
) -> None:
    response = await client.get("/api/v1/auth/me", headers=auth(admin_token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tenant_slug"] == "universe"
    assert "ADMIN" in body["role_names"]
    assert "iam" in body["services"]
    # Both code shapes authorize during the migration.
    assert {"users.read", "iam.users.read"} & set(body["permissions"])


async def test_protected_route_requires_a_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (await client.get("/api/v1/users")).status_code == 401


async def test_refresh_rotates_the_session_and_keeps_access_working(
    client: AsyncClient, viewer_token: str
) -> None:
    refreshed = await client.post("/api/v1/auth/refresh")

    assert refreshed.status_code == 200, refreshed.text
    new_token = refreshed.json()["access_token"]
    assert new_token != viewer_token
    me = await client.get("/api/v1/auth/me", headers=auth(new_token))
    assert me.status_code == 200


async def test_logout_revokes_the_access_token_immediately(
    client: AsyncClient, viewer_token: str
) -> None:
    assert (
        await client.get("/api/v1/auth/me", headers=auth(viewer_token))
    ).status_code == 200

    assert (await client.post("/api/v1/auth/logout")).status_code == 204

    # Without the session denylist the JWT would stay valid until it expired.
    after = await client.get("/api/v1/auth/me", headers=auth(viewer_token))
    assert after.status_code == 401


async def test_refresh_fails_after_logout(client: AsyncClient, viewer_token: str) -> None:
    assert viewer_token
    await client.post("/api/v1/auth/logout")

    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_every_response_carries_a_correlation_id(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.headers[REQUEST_ID_HEADER]


async def test_security_headers_are_present(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
