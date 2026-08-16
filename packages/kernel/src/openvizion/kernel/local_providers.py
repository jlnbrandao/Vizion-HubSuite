"""In-memory / config-backed entitlement and authorization providers for standalone."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from openvizion.kernel.authorization import AuthorizationDecision
from openvizion.kernel.identity import Principal


class LocalAuthorizationProvider:
    """RBAC: allow when the principal holds the permission code."""

    async def authorize(
        self,
        principal: Principal,
        action: str,
        *,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
    ) -> AuthorizationDecision:
        del resource_type, resource_id
        if principal.has_permission(action):
            return AuthorizationDecision(allowed=True, reason="rbac_grant", stage="rbac")
        return AuthorizationDecision(allowed=False, reason="missing_permission", stage="rbac")


class LocalEntitlementProvider:
    """Capability map per tenant. Never branch on commercial plan names."""

    def __init__(self, grants: Mapping[UUID, frozenset[str]] | None = None) -> None:
        self._grants: dict[UUID, frozenset[str]] = dict(grants or {})

    def grant(self, tenant_id: UUID, *capabilities: str) -> None:
        current = set(self._grants.get(tenant_id, frozenset()))
        current.update(capabilities)
        self._grants[tenant_id] = frozenset(current)

    async def has(self, tenant_id: UUID, capability: str) -> bool:
        return capability in self._grants.get(tenant_id, frozenset())

    async def list_for_tenant(self, tenant_id: UUID) -> frozenset[str]:
        return self._grants.get(tenant_id, frozenset())
