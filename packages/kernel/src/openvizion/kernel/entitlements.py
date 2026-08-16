"""EntitlementProvider — capability checks, never plan-name conditionals."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class EntitlementProvider(Protocol):
    async def has(self, tenant_id: UUID, capability: str) -> bool: ...

    async def list_for_tenant(self, tenant_id: UUID) -> frozenset[str]: ...
