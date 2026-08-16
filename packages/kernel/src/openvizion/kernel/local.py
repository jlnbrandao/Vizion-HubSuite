"""LocalPlatformAdapter — Product Kernel implementations, zero network calls."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from openvizion.kernel.audit import AuditProvider, AuditRecord
from openvizion.kernel.authorization import AuthorizationProvider
from openvizion.kernel.entitlements import EntitlementProvider
from openvizion.kernel.identity import Principal, TenantInfo
from openvizion.kernel.tenant import TenantResolver

UserLookup = Callable[[str], Awaitable[Principal]]
TenantLookup = Callable[[UUID], Awaitable[TenantInfo]]
EventPublisher = Callable[[str, UUID, dict[str, Any], str | None], Awaitable[None]]


class LocalPlatformAdapter:
    """Composes local kernel providers. Never contacts Platform Core."""

    def __init__(
        self,
        *,
        user_lookup: UserLookup,
        tenant_lookup: TenantLookup,
        authorization: AuthorizationProvider,
        entitlements: EntitlementProvider,
        audit: AuditProvider,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._user_lookup = user_lookup
        self._tenant_lookup = tenant_lookup
        self._authorization = authorization
        self._entitlements = entitlements
        self._audit = audit
        self._event_publisher = event_publisher

    async def get_current_user(self, access_token: str) -> Principal:
        return await self._user_lookup(access_token)

    async def get_tenant(self, tenant_id: UUID) -> TenantInfo:
        return await self._tenant_lookup(tenant_id)

    async def authorize(
        self,
        principal: Principal,
        action: str,
        *,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
    ) -> bool:
        decision = await self._authorization.authorize(
            principal,
            action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        return decision.allowed

    async def check_entitlement(self, tenant_id: UUID, capability: str) -> bool:
        return await self._entitlements.has(tenant_id, capability)

    async def audit(
        self,
        *,
        action: str,
        principal: Principal | None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self._audit.record(
            AuditRecord(
                action=action,
                tenant_id=principal.tenant_id if principal else None,
                user_id=principal.id if principal else None,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=metadata or {},
            )
        )

    async def publish_event(
        self,
        *,
        event_type: str,
        tenant_id: UUID,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        if self._event_publisher is None:
            return
        await self._event_publisher(event_type, tenant_id, payload, correlation_id)
