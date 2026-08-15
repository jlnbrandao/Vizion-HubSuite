"""Entitlement stage: contracted services gate whole slices before RBAC."""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from src.shared.infrastructure.security.authorization import (
    AuthorizationService,
    AuthorizationStage,
)
from src.shared.infrastructure.security.authorization_adapters import (
    CatalogEntitlementProvider,
)
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.entitlements import entitled_services
from src.shared.infrastructure.security.permission_codes import PermissionCode

TENANT_ID = uuid4()


class _FakeCatalog:
    def __init__(self, namespaces: set[str] | None = None, fail: bool = False) -> None:
        self.namespaces = namespaces or set()
        self.fail = fail
        self.calls = 0

    async def entitled_namespaces(self, tenant_id):  # noqa: ANN001, ANN201
        self.calls += 1
        if self.fail:
            raise RuntimeError("catalog unavailable")
        return frozenset(self.namespaces)


@asynccontextmanager
async def _uow_factory():
    yield None


def _provider(catalog: _FakeCatalog, ttl: int = 30) -> CatalogEntitlementProvider:
    return CatalogEntitlementProvider(catalog, _uow_factory, ttl_seconds=ttl)  # type: ignore[arg-type]


def _user(*permissions: str) -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="user@vizion.io",
        full_name="User",
        tenant_id=TENANT_ID,
        tenant_slug="acme",
        permissions=frozenset(permissions),
    )


@pytest.mark.asyncio
async def test_contracted_service_is_entitled() -> None:
    provider = _provider(_FakeCatalog({"iam"}))

    assert await provider.is_entitled(tenant_id=TENANT_ID, service="iam")
    assert not await provider.is_entitled(tenant_id=TENANT_ID, service="gps")


@pytest.mark.asyncio
async def test_answer_is_cached_until_invalidated() -> None:
    catalog = _FakeCatalog({"iam"})
    provider = _provider(catalog)

    await provider.is_entitled(tenant_id=TENANT_ID, service="iam")
    await provider.is_entitled(tenant_id=TENANT_ID, service="iam")
    assert catalog.calls == 1

    provider.invalidate(TENANT_ID)
    await provider.is_entitled(tenant_id=TENANT_ID, service="iam")
    assert catalog.calls == 2


@pytest.mark.asyncio
async def test_catalog_failure_abstains_instead_of_locking_everyone_out() -> None:
    provider = _provider(_FakeCatalog(fail=True))

    assert await provider.is_entitled(tenant_id=TENANT_ID, service="iam")


@pytest.mark.asyncio
async def test_engine_denies_at_entitlement_stage_before_rbac() -> None:
    """The user holds the permission; the tenant does not have the service."""
    service = AuthorizationService(entitlements=_provider(_FakeCatalog({"iam"})))

    decision = await service.check(
        user=_user("integration.read"), action="integration.read"
    )

    assert decision.denied
    assert decision.stage is AuthorizationStage.ENTITLEMENT


@pytest.mark.asyncio
async def test_legacy_codes_are_gated_too() -> None:
    """`users.read` resolves to the iam service through the catalog."""
    service = AuthorizationService(entitlements=_provider(_FakeCatalog({"platform"})))

    decision = await service.check(user=_user(PermissionCode.USERS_READ), action="users.read")

    assert decision.stage is AuthorizationStage.ENTITLEMENT


def test_visible_services_require_both_contract_and_permission() -> None:
    permissions = {PermissionCode.USERS_READ, PermissionCode.INTEGRATION_READ}

    assert entitled_services(permissions, {"iam", "platform"}) == frozenset({"iam"})
    # Without a catalog the permissions alone decide (bootstrap / degraded mode).
    assert entitled_services(permissions) == frozenset({"iam", "integration"})
