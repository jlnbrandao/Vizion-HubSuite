"""Billing is a tenant-only slice: product tenants see it, PLATFORM does not."""

from __future__ import annotations

from httpx import AsyncClient

from tests.integration.conftest import auth


async def test_product_admin_can_read_billing_overview(
    client: AsyncClient, admin_token: str
) -> None:
    response = await client.get("/api/v1/billing/overview", headers=auth(admin_token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert "total" in body
    assert "users" in body
    assert "services" in body
    slugs = {item["ref"] for item in body["services"]}
    assert "billing" in slugs


async def test_product_viewer_is_denied_billing(
    client: AsyncClient, viewer_token: str
) -> None:
    response = await client.get("/api/v1/billing/overview", headers=auth(viewer_token))
    assert response.status_code == 403


async def test_platform_operator_cannot_open_billing(
    platform_client: AsyncClient, platform_token: str
) -> None:
    overview = await platform_client.get(
        "/api/v1/billing/overview", headers=auth(platform_token)
    )
    assert overview.status_code == 403

    navigation = await platform_client.get(
        "/api/v1/navigation", headers=auth(platform_token)
    )
    assert navigation.status_code == 200, navigation.text
    ids = {item["id"] for item in navigation.json()["items"]}
    assert "account-billing" not in ids

    me = await platform_client.get("/api/v1/auth/me", headers=auth(platform_token))
    assert "billing" not in me.json().get("services", [])


async def test_billing_cannot_be_entitled_on_the_platform_tenant(
    platform_client: AsyncClient, platform_token: str
) -> None:
    me = await platform_client.get("/api/v1/auth/me", headers=auth(platform_token))
    tenant_id = me.json()["tenant_id"]

    response = await platform_client.put(
        f"/api/v1/services/tenants/{tenant_id}/billing",
        headers=auth(platform_token),
        json={"status": "active"},
    )
    assert response.status_code == 422
    assert "tenant-only" in response.json()["error"]["message"]


async def test_billing_cannot_be_suspended_on_a_product_tenant(
    client: AsyncClient,
    admin_token: str,
    platform_client: AsyncClient,
    platform_token: str,
) -> None:
    me = await client.get("/api/v1/auth/me", headers=auth(admin_token))
    tenant_id = me.json()["tenant_id"]

    response = await platform_client.put(
        f"/api/v1/services/tenants/{tenant_id}/billing",
        headers=auth(platform_token),
        json={"status": "suspended"},
    )
    assert response.status_code == 422
    assert "mandatory" in response.json()["error"]["message"]


async def test_asaas_webhook_rejects_a_bad_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/billing/webhooks/asaas",
        json={"event": "PAYMENT_CONFIRMED", "payment": {"id": "pay_1"}},
        headers={"asaas-access-token": "wrong"},
    )
    assert response.status_code in {401, 503}
