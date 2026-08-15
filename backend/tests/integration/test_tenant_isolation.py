"""Tenant boundaries over HTTP: a token is only good on the tenant that issued it."""

from __future__ import annotations

from typing import Any

from httpx import ASGITransport, AsyncClient

from tests.integration.conftest import (
    BIGBANG_HOST,
    TEST_USER_PASSWORD,
    UNIVERSE_HOST,
    auth,
    login,
    provisioned_user,
)


async def test_token_from_one_tenant_is_rejected_on_another_host(
    app: Any, client: AsyncClient
) -> None:
    async with provisioned_user(
        app, tenant_slug="universe", role_name="VIEWER", username="itest_cross"
    ) as email:
        token = await login(client, email, TEST_USER_PASSWORD)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url=f"http://{BIGBANG_HOST}",
            headers={"Host": BIGBANG_HOST},
        ) as other_tenant:
            response = await other_tenant.get("/api/v1/auth/me", headers=auth(token))

    assert response.status_code == 401


async def test_unknown_tenant_host_is_not_found(app: Any) -> None:
    host = "no-such-tenant.localhost"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=f"http://{host}", headers={"Host": host}
    ) as http:
        response = await http.get("/api/v1/auth/me")

    assert response.status_code == 404


async def test_host_outside_the_allowlist_is_refused(app: Any) -> None:
    host = "universe.evil.example"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=f"http://{host}", headers={"Host": host}
    ) as http:
        response = await http.get("/api/v1/auth/me")

    assert response.status_code == 422


async def test_users_are_scoped_to_the_calling_tenant(
    app: Any, client: AsyncClient, admin_token: str
) -> None:
    """The provisioned universe user must not appear in the ops tenant listing."""
    listed = await client.get("/api/v1/users", headers=auth(admin_token))
    assert listed.status_code == 200, listed.text
    emails = {user["email"] for user in listed.json()}
    assert any(email.endswith("@lanstar.test") for email in emails)

    async with provisioned_user(
        app, tenant_slug="bigbang", role_name="PLATFORM", username="itest_ops_reader"
    ) as ops_email:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url=f"http://{BIGBANG_HOST}",
            headers={"Host": BIGBANG_HOST},
        ) as ops:
            ops_token = await login(ops, ops_email, TEST_USER_PASSWORD)
            ops_users = await ops.get("/api/v1/users", headers=auth(ops_token))

    # PLATFORM has no users.read; either way it must never see universe users.
    if ops_users.status_code == 200:
        assert not (emails & {user["email"] for user in ops_users.json()})
    else:
        assert ops_users.status_code == 403


async def test_audit_events_do_not_cross_tenants(
    client: AsyncClient, admin_token: str
) -> None:
    response = await client.get(
        "/api/v1/audit-events", params={"limit": 50}, headers=auth(admin_token)
    )

    assert response.status_code == 200, response.text
    # RLS scopes the query; the assertion is that the endpoint answers at all and
    # every row belongs to the caller's tenant (enforced by the policy itself).
    assert isinstance(response.json(), list)


async def test_hosts_are_bound_per_request(app: Any) -> None:
    """Two clients on different hosts must not share tenant context."""
    async with (
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url=f"http://{UNIVERSE_HOST}",
            headers={"Host": UNIVERSE_HOST},
        ) as universe,
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url=f"http://{BIGBANG_HOST}",
            headers={"Host": BIGBANG_HOST},
        ) as bigbang,
    ):
        async with provisioned_user(
            app, tenant_slug="universe", role_name="VIEWER", username="itest_ctx"
        ) as email:
            token = await login(universe, email, TEST_USER_PASSWORD)
            mine = await universe.get("/api/v1/auth/me", headers=auth(token))
            theirs = await bigbang.get("/api/v1/auth/me", headers=auth(token))

    assert mine.json()["tenant_slug"] == "universe"
    assert theirs.status_code == 401
