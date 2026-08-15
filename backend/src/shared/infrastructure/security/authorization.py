"""AuthorizationService — the single place where access decisions are made.

Precedence is fixed and must not be reordered by configuration or policy:

  1. TENANT      tenant isolation, hard-fail, never overridable
  2. ENTITLEMENT the tenant must have the service contracted (hard-fail)
  3. ACL deny    an explicit deny beats everything below it
  4. ACL allow   an explicit, resource-scoped administrative exception
  5. RBAC        effective permission codes from roles
  6. ABAC        contextual policies; may deny what RBAC granted, never grants alone

ACL allow short-circuits RBAC and ABAC on purpose: it exists to grant one subject
access to one resource without handing out a global permission. Tenant isolation
still applies, so an ACL can never leak across tenants.

Endpoints must not re-implement any of this; they call `require_permission(...)`
(which delegates here) or `AuthorizationService.authorize(...)` for resource checks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID

from src.shared.infrastructure.exceptions import ForbiddenError
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.security.role_hierarchy import ROLE_RANK, role_rank


class AuthorizationStage(StrEnum):
    TENANT = "tenant"
    ENTITLEMENT = "entitlement"
    ACL = "acl"
    RBAC = "rbac"
    ABAC = "abac"


class AclEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    stage: AuthorizationStage
    reason: str

    @property
    def denied(self) -> bool:
        return not self.allowed


@dataclass(frozen=True, slots=True)
class ResourceRef:
    """The thing being acted upon, described in terms the engine understands."""

    type: str
    id: UUID | None = None
    tenant_id: UUID | None = None
    owner_id: UUID | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def to_abac_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "type": self.type,
            "id": str(self.id) if self.id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "owner_id": self.owner_id,
        }
        attrs.update(self.attributes)
        return attrs


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Environment attributes available to ABAC policies."""

    ip: str | None = None
    user_agent: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def to_environment(self) -> dict[str, Any]:
        env: dict[str, Any] = {"ip": self.ip, "user_agent": self.user_agent}
        env.update(self.extra)
        return env


# --- Ports -------------------------------------------------------------------


class AclProvider(ABC):
    """Resource-scoped exceptions. Phase 3 backs this with `resource_acls`."""

    @abstractmethod
    async def effect_for(
        self,
        *,
        user: CurrentUser,
        action: str,
        resource: ResourceRef,
    ) -> AclEffect | None:
        """Return the winning ACL effect, or None when no entry applies."""


class NullAclProvider(AclProvider):
    async def effect_for(
        self,
        *,
        user: CurrentUser,
        action: str,
        resource: ResourceRef,
    ) -> AclEffect | None:
        return None


class EntitlementProvider(ABC):
    """Service catalog gate. Phase 6 backs this with `tenant_services`."""

    @abstractmethod
    async def is_entitled(self, *, tenant_id: UUID, service: str) -> bool: ...


class AllowAllEntitlementProvider(EntitlementProvider):
    async def is_entitled(self, *, tenant_id: UUID, service: str) -> bool:
        return True


class AbacGate(ABC):
    """Contextual policy evaluation. Returns True when nothing objects."""

    @abstractmethod
    async def allows(
        self,
        *,
        subject_attributes: Mapping[str, Any],
        action: str,
        resource_attributes: Mapping[str, Any],
        environment: Mapping[str, Any],
    ) -> bool: ...


class AllowAllAbacGate(AbacGate):
    async def allows(
        self,
        *,
        subject_attributes: Mapping[str, Any],
        action: str,
        resource_attributes: Mapping[str, Any],
        environment: Mapping[str, Any],
    ) -> bool:
        return True


class AuthorizationAuditSink(ABC):
    @abstractmethod
    async def record_denied(
        self,
        *,
        user: CurrentUser,
        action: str,
        resource: ResourceRef | None,
        decision: Decision,
        context: RequestContext | None,
    ) -> None: ...


class NullAuthorizationAuditSink(AuthorizationAuditSink):
    async def record_denied(
        self,
        *,
        user: CurrentUser,
        action: str,
        resource: ResourceRef | None,
        decision: Decision,
        context: RequestContext | None,
    ) -> None:
        return None


# --- Engine ------------------------------------------------------------------


def service_for_permission(code: str) -> str | None:
    """Service namespace of a permission code.

    Namespaced codes carry it directly; legacy `resource.action` codes resolve
    through the catalog map. None means "unknown service" and the entitlement
    stage abstains — RBAC still applies.
    """
    return PermissionCode.service_of(code)


class HierarchyPolicy:
    """Privilege-hierarchy rule, owned by the authorization engine.

    Callers resolve the target's role names (a data concern) and delegate the
    decision here so the rule has exactly one definition.
    """

    @staticmethod
    def rank(role_names: Iterable[str]) -> int:
        return role_rank(role_names)

    @staticmethod
    def can_manage(actor_roles: Iterable[str], target_roles: Iterable[str]) -> bool:
        """True when the actor strictly outranks the target."""
        return role_rank(actor_roles) > role_rank(target_roles)

    @staticmethod
    def can_grant(actor_roles: Iterable[str], granted_roles: Iterable[str]) -> bool:
        """True when the actor strictly outranks every role being granted."""
        actor = role_rank(actor_roles)
        return all(actor > ROLE_RANK.get(name.upper(), 0) for name in granted_roles)


class AuthorizationService:
    def __init__(
        self,
        acl_provider: AclProvider | None = None,
        entitlements: EntitlementProvider | None = None,
        abac_gate: AbacGate | None = None,
        audit_sink: AuthorizationAuditSink | None = None,
    ) -> None:
        self._acls = acl_provider or NullAclProvider()
        self._entitlements = entitlements or AllowAllEntitlementProvider()
        self._abac = abac_gate or AllowAllAbacGate()
        self._audit = audit_sink or NullAuthorizationAuditSink()

    async def check(
        self,
        *,
        user: CurrentUser,
        action: str,
        resource: ResourceRef | None = None,
        context: RequestContext | None = None,
    ) -> Decision:
        decision = await self._evaluate(
            user=user, action=action, resource=resource, context=context
        )
        if decision.denied:
            await self._audit.record_denied(
                user=user,
                action=action,
                resource=resource,
                decision=decision,
                context=context,
            )
        return decision

    async def authorize(
        self,
        *,
        user: CurrentUser,
        action: str,
        resource: ResourceRef | None = None,
        context: RequestContext | None = None,
    ) -> None:
        decision = await self.check(
            user=user, action=action, resource=resource, context=context
        )
        if decision.denied:
            raise ForbiddenError(decision.reason)

    async def authorize_all(
        self,
        *,
        user: CurrentUser,
        actions: Sequence[str],
        resource: ResourceRef | None = None,
        context: RequestContext | None = None,
    ) -> None:
        """Every action must be allowed. Reports all missing codes at once."""
        denials: list[tuple[str, Decision]] = []
        for action in actions:
            decision = await self.check(
                user=user, action=action, resource=resource, context=context
            )
            if decision.denied:
                denials.append((action, decision))
        if not denials:
            return

        # A hard-fail stage is the real cause; do not dilute it with a code list.
        for _, decision in denials:
            if decision.stage in (
                AuthorizationStage.TENANT,
                AuthorizationStage.ENTITLEMENT,
            ):
                raise ForbiddenError(decision.reason)

        if all(decision.stage is AuthorizationStage.RBAC for _, decision in denials):
            missing = ", ".join(action for action, _ in denials)
            raise ForbiddenError(f"Missing permission(s): {missing}")

        raise ForbiddenError(denials[0][1].reason)

    async def authorize_any(
        self,
        *,
        user: CurrentUser,
        actions: Sequence[str],
        resource: ResourceRef | None = None,
        context: RequestContext | None = None,
    ) -> None:
        """At least one action must be allowed."""
        for action in actions:
            decision = await self._evaluate(
                user=user, action=action, resource=resource, context=context
            )
            if decision.allowed:
                return
        decision = Decision(
            allowed=False,
            stage=AuthorizationStage.RBAC,
            reason=f"Requires one of permissions: {', '.join(actions)}",
        )
        await self._audit.record_denied(
            user=user,
            action=" | ".join(actions),
            resource=resource,
            decision=decision,
            context=context,
        )
        raise ForbiddenError(decision.reason)

    async def _evaluate(
        self,
        *,
        user: CurrentUser,
        action: str,
        resource: ResourceRef | None,
        context: RequestContext | None,
    ) -> Decision:
        # 1. Tenant isolation — never overridable.
        crosses_tenant = (
            resource is not None
            and resource.tenant_id is not None
            and resource.tenant_id != user.tenant_id
        )
        if crosses_tenant:
            return Decision(
                allowed=False,
                stage=AuthorizationStage.TENANT,
                reason="Resource belongs to another tenant",
            )

        # 2. Service entitlement.
        service = service_for_permission(action)
        if service is not None:
            entitled = await self._entitlements.is_entitled(
                tenant_id=user.tenant_id, service=service
            )
            if not entitled:
                return Decision(
                    allowed=False,
                    stage=AuthorizationStage.ENTITLEMENT,
                    reason=f"Service not enabled for this tenant: {service}",
                )

        # 3/4. Explicit ACL entries.
        if resource is not None:
            effect = await self._acls.effect_for(user=user, action=action, resource=resource)
            if effect is AclEffect.DENY:
                return Decision(
                    allowed=False,
                    stage=AuthorizationStage.ACL,
                    reason=f"Access denied by ACL for {resource.type}",
                )
            if effect is AclEffect.ALLOW:
                return Decision(
                    allowed=True,
                    stage=AuthorizationStage.ACL,
                    reason="Allowed by ACL exception",
                )

        # 5. RBAC.
        if not user.has_permission(action):
            return Decision(
                allowed=False,
                stage=AuthorizationStage.RBAC,
                reason=f"Missing permission(s): {action}",
            )

        # 6. ABAC — only meaningful with a concrete resource.
        if resource is not None:
            allowed = await self._abac.allows(
                subject_attributes=_subject_attributes(user),
                action=action,
                resource_attributes=resource.to_abac_attributes(),
                environment=(context or RequestContext()).to_environment(),
            )
            if not allowed:
                return Decision(
                    allowed=False,
                    stage=AuthorizationStage.ABAC,
                    reason="Access denied by policy",
                )

        return Decision(allowed=True, stage=AuthorizationStage.RBAC, reason="Allowed")


def _subject_attributes(user: CurrentUser) -> dict[str, Any]:
    return {
        "user_id": user.id,
        "tenant_id": str(user.tenant_id),
        "role_names": sorted(user.role_names),
        "permissions": sorted(user.permissions),
    }
