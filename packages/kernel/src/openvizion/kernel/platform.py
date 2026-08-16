"""PlatformAdapter — capabilities that may be local or provided by Platform Core.

Domain and use cases depend only on this protocol. The composition root binds
LocalPlatformAdapter or HubPlatformAdapter from environment variables.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from openvizion.kernel.identity import Principal, TenantInfo


class PlatformAdapter(Protocol):
    async def get_current_user(self, access_token: str) -> Principal: ...

    async def get_tenant(self, tenant_id: UUID) -> TenantInfo: ...

    async def authorize(
        self,
        principal: Principal,
        action: str,
        *,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
    ) -> bool: ...

    async def check_entitlement(self, tenant_id: UUID, capability: str) -> bool: ...

    async def audit(
        self,
        *,
        action: str,
        principal: Principal | None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    async def publish_event(
        self,
        *,
        event_type: str,
        tenant_id: UUID,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None: ...
