"""Tenant resolution — Host → tenant. tenant_id is never taken from the client body."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from openvizion.kernel.identity import TenantInfo


@dataclass(frozen=True, slots=True)
class TenantContext:
    id: UUID
    slug: str
    name: str


class TenantResolver(Protocol):
    async def resolve_by_slug(self, slug: str) -> TenantInfo: ...
