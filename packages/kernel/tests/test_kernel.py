from uuid import UUID, uuid4

import pytest

from openvizion.kernel.configuration import AdapterSelection, DeploymentMode, KernelSettings
from openvizion.kernel.identity import Principal
from openvizion.kernel.local_providers import LocalAuthorizationProvider, LocalEntitlementProvider


TENANT = UUID("a0000000-0000-4000-8000-000000000001")


def _principal(*permissions: str) -> Principal:
    return Principal(
        id=uuid4(),
        email="admin@example.test",
        full_name="Admin",
        tenant_id=TENANT,
        tenant_slug="demo",
        permissions=frozenset(permissions),
        role_names=frozenset({"ADMIN"}),
    )


def test_standalone_rejects_hub_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEPLOYMENT_MODE", "standalone")
    monkeypatch.setenv("PLATFORM_ADAPTER", "local")
    monkeypatch.setenv("PLATFORM_CORE_URL", "http://platform-core:8000")
    settings = KernelSettings(_env_file=None)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="forbids PLATFORM_CORE_URL"):
        settings.require_standalone_isolation()


def test_standalone_requires_local_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEPLOYMENT_MODE", "standalone")
    monkeypatch.setenv("PLATFORM_ADAPTER", "hub")
    monkeypatch.setenv("PLATFORM_CORE_URL", "")
    settings = KernelSettings(_env_file=None)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="PLATFORM_ADAPTER=local"):
        settings.require_standalone_isolation()


def test_integrated_requires_core_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEPLOYMENT_MODE", "integrated")
    monkeypatch.setenv("PLATFORM_ADAPTER", "hub")
    monkeypatch.setenv("PLATFORM_CORE_URL", "")
    settings = KernelSettings(_env_file=None)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="PLATFORM_CORE_URL"):
        settings.require_integrated_hub()


@pytest.mark.asyncio
async def test_local_authorization_rbac() -> None:
    provider = LocalAuthorizationProvider()
    allowed = _principal("tracking.devices.read")
    denied = _principal()
    ok = await provider.authorize(allowed, "tracking.devices.read")
    no = await provider.authorize(denied, "tracking.devices.read")
    assert ok.allowed is True
    assert no.allowed is False


@pytest.mark.asyncio
async def test_entitlements_are_capabilities_not_plans() -> None:
    provider = LocalEntitlementProvider()
    provider.grant(TENANT, "ADVANCED_TELEMETRY")
    assert await provider.has(TENANT, "ADVANCED_TELEMETRY")
    assert not await provider.has(TENANT, "SNMP_TRAPS")


def test_adapter_selection_values() -> None:
    assert DeploymentMode.STANDALONE == "standalone"
    assert AdapterSelection.LOCAL == "local"
    assert AdapterSelection.HUB == "hub"
