from uuid import uuid4

import httpx
import pytest

from openvizion.kernel.hub import HubPlatformAdapter
from openvizion.kernel.identity import Principal


@pytest.mark.asyncio
async def test_integrated_adapter_calls_platform_core() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/hub/token"):
            return httpx.Response(200, json={"access_token": "svc-token"})
        if request.url.path.endswith("/hub/authorize"):
            return httpx.Response(200, json={"allowed": True})
        if request.url.path.endswith("/hub/entitlements/check"):
            return httpx.Response(200, json={"entitled": True})
        return httpx.Response(404)

    adapter = HubPlatformAdapter(
        base_url="http://platform-core:8000",
        client_id="tracking",
        client_secret="secret",
        retries=0,
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://platform-core:8000",
        ),
    )
    principal = Principal(
        id=uuid4(),
        email="a@b.c",
        full_name="A",
        tenant_id=uuid4(),
        tenant_slug="demo",
        permissions=frozenset(),
    )
    assert await adapter.authorize(principal, "tracking.devices.read") is True
    assert await adapter.check_entitlement(principal.tenant_id, "ADVANCED_TELEMETRY") is True
    assert any(path.endswith("/hub/authorize") for path in calls)
    assert any(path.endswith("/hub/token") for path in calls)
    await adapter.aclose()
