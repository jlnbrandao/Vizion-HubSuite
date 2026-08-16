from uuid import uuid4

import httpx
import pytest

from openvizion.kernel.hub import HubPlatformAdapter, HubUnavailableError
from openvizion.kernel.identity import Principal


TENANT = uuid4()
USER = uuid4()


def _principal() -> Principal:
    return Principal(
        id=USER,
        email="u@example.test",
        full_name="U",
        tenant_id=TENANT,
        tenant_slug="demo",
        permissions=frozenset({"tracking.devices.read"}),
    )


def _adapter(handler: httpx.MockTransport) -> HubPlatformAdapter:
    client = httpx.AsyncClient(transport=handler, base_url="http://hub.test")
    return HubPlatformAdapter(
        base_url="http://hub.test",
        client_id="cid",
        client_secret="secret",
        timeout_seconds=0.2,
        retries=2,
        cache_ttl_seconds=30,
        client=client,
    )


@pytest.mark.asyncio
async def test_hub_adapter_authorize_and_cache() -> None:
    calls = {"authorize": 0, "token": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/hub/token"):
            calls["token"] += 1
            return httpx.Response(200, json={"access_token": "svc"})
        if request.url.path.endswith("/hub/authorize"):
            calls["authorize"] += 1
            return httpx.Response(200, json={"allowed": True, "reason": "rbac"})
        return httpx.Response(404)

    adapter = _adapter(httpx.MockTransport(handler))
    principal = _principal()
    assert await adapter.authorize(principal, "tracking.devices.read") is True
    assert await adapter.authorize(principal, "tracking.devices.read") is True
    assert calls["authorize"] == 1
    assert calls["token"] == 1
    await adapter.aclose()


@pytest.mark.asyncio
async def test_hub_adapter_fail_closed_on_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    adapter = HubPlatformAdapter(
        base_url="http://hub.test",
        client_id="cid",
        client_secret="secret",
        timeout_seconds=0.05,
        retries=1,
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://hub.test",
        ),
    )
    assert await adapter.authorize(_principal(), "tracking.devices.read") is False
    assert await adapter.check_entitlement(TENANT, "ADVANCED_TELEMETRY") is False
    await adapter.aclose()


@pytest.mark.asyncio
async def test_hub_adapter_retries_then_raises_on_token() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        raise httpx.ConnectError("down")

    adapter = HubPlatformAdapter(
        base_url="http://hub.test",
        client_id="cid",
        client_secret="secret",
        timeout_seconds=0.05,
        retries=2,
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://hub.test",
        ),
    )
    with pytest.raises(HubUnavailableError):
        await adapter.get_current_user("tok")
    assert attempts["n"] == 3
    await adapter.aclose()
