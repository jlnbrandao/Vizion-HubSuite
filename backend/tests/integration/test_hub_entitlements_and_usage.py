"""Hub behaviour end to end: entitlements gate the engine, metered calls are billed."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from tests.integration.conftest import auth


async def test_my_services_lists_the_core_contract(
    client: AsyncClient, admin_token: str
) -> None:
    response = await client.get("/api/v1/services/me", headers=auth(admin_token))

    assert response.status_code == 200, response.text
    services = {item["slug"]: item for item in response.json()}
    assert {"iam", "platform", "integration", "billing"} <= set(services)
    assert services["iam"]["entitled"] is True
    assert services["iam"]["is_core"] is True
    assert services["billing"]["entitled"] is True


async def test_navigation_only_offers_entitled_and_permitted_entries(
    client: AsyncClient, viewer_token: str
) -> None:
    response = await client.get("/api/v1/navigation", headers=auth(viewer_token))

    assert response.status_code == 200, response.text
    body = response.json()
    ids = {item["id"] for item in body["items"]}
    assert "nav-home" in ids
    assert "admin-users" in ids  # VIEWER holds users.read
    assert "platform-tenants" not in ids  # platform codes are not granted here
    assert body["home_route"] == "/dashboard"


async def test_suspending_a_service_blocks_it_before_rbac(
    app: Any, platform_client: AsyncClient, platform_token: str
) -> None:
    """ENTITLEMENT is a hard-fail stage: the permission is held, the service is not."""
    me = await platform_client.get("/api/v1/auth/me", headers=auth(platform_token))
    assert me.status_code == 200, me.text
    ops_tenant_id = me.json()["tenant_id"]

    before = await platform_client.get("/api/v1/integrations", headers=auth(platform_token))
    assert before.status_code == 200, before.text

    suspend = await platform_client.put(
        f"/api/v1/services/tenants/{ops_tenant_id}/integration",
        headers=auth(platform_token),
        json={"status": "suspended"},
    )
    try:
        assert suspend.status_code == 200, suspend.text

        blocked = await platform_client.get(
            "/api/v1/integrations", headers=auth(platform_token)
        )
        assert blocked.status_code == 403
        assert "integration" in blocked.json()["error"]["message"]

        # IAM is untouched: only the suspended namespace is refused.
        assert (
            await platform_client.get("/api/v1/auth/me", headers=auth(platform_token))
        ).status_code == 200
    finally:
        restored = await platform_client.put(
            f"/api/v1/services/tenants/{ops_tenant_id}/integration",
            headers=auth(platform_token),
            json={"status": "active"},
        )
        assert restored.status_code == 200, restored.text
        app.state.container.entitlement_provider().invalidate()

    after = await platform_client.get("/api/v1/integrations", headers=auth(platform_token))
    assert after.status_code == 200


async def test_core_services_cannot_be_disabled(
    platform_client: AsyncClient, platform_token: str
) -> None:
    me = await platform_client.get("/api/v1/auth/me", headers=auth(platform_token))
    ops_tenant_id = me.json()["tenant_id"]

    response = await platform_client.put(
        f"/api/v1/services/tenants/{ops_tenant_id}/iam",
        headers=auth(platform_token),
        json={"status": "disabled"},
    )

    assert response.status_code == 422
    assert "core" in response.json()["error"]["message"].lower()


async def test_usage_report_is_scoped_to_the_caller(
    client: AsyncClient, admin_token: str
) -> None:
    response = await client.get("/api/v1/usage", headers=auth(admin_token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["since"] < body["until"]
    assert isinstance(body["totals_by_service"], dict)
    for record in body["records"]:
        assert record["quantity"] >= 0


async def test_tenant_usage_requires_the_platform_code(
    client: AsyncClient, admin_token: str
) -> None:
    me = await client.get("/api/v1/auth/me", headers=auth(admin_token))
    tenant_id = me.json()["tenant_id"]

    response = await client.get(
        f"/api/v1/usage/tenants/{tenant_id}", headers=auth(admin_token)
    )

    assert response.status_code == 403


async def test_metered_operation_is_recorded_in_usage(
    app: Any, platform_client: AsyncClient, platform_token: str
) -> None:
    """A metered integration call must show up in the tenant's usage report."""
    integrations = await platform_client.get(
        "/api/v1/integrations", headers=auth(platform_token)
    )
    assert integrations.status_code == 200, integrations.text
    rows = integrations.json()
    if not rows:
        return  # nothing configured in this environment; quota path is unit-tested

    integration_id = rows[0]["id"]
    me = await platform_client.get("/api/v1/auth/me", headers=auth(platform_token))
    assert me.status_code == 200, me.text
    tenant_id = me.json()["tenant_id"]

    before = await platform_client.get(
        f"/api/v1/usage/tenants/{tenant_id}",
        params={"service": "integration"},
        headers=auth(platform_token),
    )
    assert before.status_code == 200, before.text
    previous = before.json()["totals_by_service"].get("integration", 0)

    # The sync itself may fail (no reachable endpoint); the quota is consumed first.
    await platform_client.post(
        f"/api/v1/integrations/{integration_id}/sync", headers=auth(platform_token)
    )

    after = await platform_client.get(
        f"/api/v1/usage/tenants/{tenant_id}",
        params={"service": "integration"},
        headers=auth(platform_token),
    )
    assert after.json()["totals_by_service"].get("integration", 0) > previous
