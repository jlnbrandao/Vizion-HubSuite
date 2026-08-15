"""AuthorizationService — precedence matrix.

Order under test: TENANT > ENTITLEMENT > ACL deny > ACL allow > RBAC > ABAC.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.shared.infrastructure.exceptions import ForbiddenError
from src.shared.infrastructure.security.authorization import (
    AbacGate,
    AclEffect,
    AclProvider,
    AuthorizationService,
    AuthorizationStage,
    Decision,
    EntitlementProvider,
    NullAuthorizationAuditSink,
    RequestContext,
    ResourceRef,
    service_for_permission,
)
from src.shared.infrastructure.security.current_user import CurrentUser

TENANT_A = UUID("a0000000-0000-4000-8000-00000000000a")
TENANT_B = UUID("b0000000-0000-4000-8000-00000000000b")


def _user(*permissions: str, tenant_id: UUID = TENANT_A) -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="u@x.com",
        full_name="User",
        tenant_id=tenant_id,
        tenant_slug="universe",
        tenant_name="Universe",
        role_names=frozenset({"OPERATOR"}),
        permissions=frozenset(permissions),
    )


class FixedAcl(AclProvider):
    def __init__(self, effect: AclEffect | None) -> None:
        self._effect = effect

    async def effect_for(self, *, user: CurrentUser, action: str, resource: ResourceRef):
        return self._effect


class DenyEntitlements(EntitlementProvider):
    async def is_entitled(self, *, tenant_id: UUID, service: str) -> bool:
        return False


class DenyAbac(AbacGate):
    async def allows(
        self,
        *,
        subject_attributes: Mapping[str, Any],
        action: str,
        resource_attributes: Mapping[str, Any],
        environment: Mapping[str, Any],
    ) -> bool:
        return False


class RecordingSink(NullAuthorizationAuditSink):
    def __init__(self) -> None:
        self.denials: list[Decision] = []

    async def record_denied(self, *, user, action, resource, decision, context) -> None:
        self.denials.append(decision)


def _vehicle(tenant_id: UUID = TENANT_A) -> ResourceRef:
    return ResourceRef(type="vehicle", id=uuid4(), tenant_id=tenant_id)


@pytest.mark.asyncio
async def test_rbac_allows_when_permission_present() -> None:
    service = AuthorizationService()
    decision = await service.check(user=_user("vehicle.read"), action="vehicle.read")

    assert decision.allowed


@pytest.mark.asyncio
async def test_rbac_denies_when_permission_missing() -> None:
    service = AuthorizationService()
    decision = await service.check(user=_user(), action="vehicle.read")

    assert decision.denied
    assert decision.stage is AuthorizationStage.RBAC
    assert "vehicle.read" in decision.reason


@pytest.mark.asyncio
async def test_cross_tenant_resource_is_denied_even_with_permission() -> None:
    service = AuthorizationService()
    decision = await service.check(
        user=_user("vehicle.read"),
        action="vehicle.read",
        resource=_vehicle(tenant_id=TENANT_B),
    )

    assert decision.denied
    assert decision.stage is AuthorizationStage.TENANT


@pytest.mark.asyncio
async def test_tenant_isolation_outranks_an_acl_allow() -> None:
    service = AuthorizationService(acl_provider=FixedAcl(AclEffect.ALLOW))
    decision = await service.check(
        user=_user("vehicle.read"),
        action="vehicle.read",
        resource=_vehicle(tenant_id=TENANT_B),
    )

    assert decision.denied
    assert decision.stage is AuthorizationStage.TENANT


@pytest.mark.asyncio
async def test_acl_deny_beats_rbac_grant() -> None:
    service = AuthorizationService(acl_provider=FixedAcl(AclEffect.DENY))
    decision = await service.check(
        user=_user("vehicle.update"), action="vehicle.update", resource=_vehicle()
    )

    assert decision.denied
    assert decision.stage is AuthorizationStage.ACL


@pytest.mark.asyncio
async def test_acl_allow_grants_without_rbac_permission() -> None:
    service = AuthorizationService(acl_provider=FixedAcl(AclEffect.ALLOW))
    decision = await service.check(
        user=_user(), action="vehicle.update", resource=_vehicle()
    )

    assert decision.allowed
    assert decision.stage is AuthorizationStage.ACL


@pytest.mark.asyncio
async def test_abac_can_deny_what_rbac_allowed() -> None:
    service = AuthorizationService(abac_gate=DenyAbac())
    decision = await service.check(
        user=_user("vehicle.read"), action="vehicle.read", resource=_vehicle()
    )

    assert decision.denied
    assert decision.stage is AuthorizationStage.ABAC


@pytest.mark.asyncio
async def test_abac_never_grants_on_its_own() -> None:
    """Without the RBAC code, a permissive ABAC gate changes nothing."""
    service = AuthorizationService()
    decision = await service.check(
        user=_user(), action="vehicle.read", resource=_vehicle()
    )

    assert decision.denied
    assert decision.stage is AuthorizationStage.RBAC


@pytest.mark.asyncio
async def test_missing_entitlement_denies_before_rbac() -> None:
    service = AuthorizationService(entitlements=DenyEntitlements())
    decision = await service.check(user=_user("gps.vehicles.read"), action="gps.vehicles.read")

    assert decision.denied
    assert decision.stage is AuthorizationStage.ENTITLEMENT
    assert "gps" in decision.reason


@pytest.mark.asyncio
async def test_entitlement_stage_is_skipped_for_legacy_codes() -> None:
    """Two-part codes carry no service namespace, so the gate must not fire."""
    service = AuthorizationService(entitlements=DenyEntitlements())
    decision = await service.check(user=_user("vehicle.read"), action="vehicle.read")

    assert decision.allowed


@pytest.mark.asyncio
async def test_denials_are_audited() -> None:
    sink = RecordingSink()
    service = AuthorizationService(audit_sink=sink)

    await service.check(user=_user(), action="vehicle.read")

    assert len(sink.denials) == 1
    assert sink.denials[0].stage is AuthorizationStage.RBAC


@pytest.mark.asyncio
async def test_authorize_all_reports_every_missing_code() -> None:
    service = AuthorizationService()

    with pytest.raises(ForbiddenError) as exc:
        await service.authorize_all(
            user=_user("users.read"), actions=("users.read", "users.create", "users.delete")
        )

    assert "users.create" in str(exc.value)
    assert "users.delete" in str(exc.value)
    assert "users.read" not in str(exc.value).replace("users.read,", "")


@pytest.mark.asyncio
async def test_authorize_all_surfaces_hard_failure_first() -> None:
    service = AuthorizationService(entitlements=DenyEntitlements())

    with pytest.raises(ForbiddenError, match="Service not enabled"):
        await service.authorize_all(
            user=_user(), actions=("gps.vehicles.read", "gps.vehicles.update")
        )


@pytest.mark.asyncio
async def test_authorize_any_passes_with_a_single_grant() -> None:
    service = AuthorizationService()

    await service.authorize_any(
        user=_user("users.read"), actions=("users.create", "users.read")
    )

    with pytest.raises(ForbiddenError, match="Requires one of permissions"):
        await service.authorize_any(user=_user(), actions=("users.create", "users.read"))


@pytest.mark.asyncio
async def test_context_environment_reaches_the_abac_gate() -> None:
    seen: dict[str, Any] = {}

    class CapturingGate(AbacGate):
        async def allows(
            self, *, subject_attributes, action, resource_attributes, environment
        ) -> bool:
            seen.update(environment)
            return True

    service = AuthorizationService(abac_gate=CapturingGate())
    await service.check(
        user=_user("vehicle.read"),
        action="vehicle.read",
        resource=_vehicle(),
        context=RequestContext(ip="203.0.113.7", user_agent="pytest"),
    )

    assert seen["ip"] == "203.0.113.7"
    assert seen["user_agent"] == "pytest"


def test_service_for_permission_namespaces() -> None:
    assert service_for_permission("gps.vehicles.read") == "gps"
    # Legacy codes resolve through the catalog, so entitlement gates them too.
    assert service_for_permission("users.read") == "iam"
    assert service_for_permission("vehicle.read") is None
