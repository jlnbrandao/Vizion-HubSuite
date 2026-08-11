"""Tenant repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.modules.tenants.entities.tenant import Tenant
from src.modules.tenants.value_objects.tenant_slug import TenantSlug
from src.shared.domain.repository import Repository


class TenantRepository(Repository[Tenant], ABC):
    @abstractmethod
    async def get_by_slug(self, slug: TenantSlug) -> Tenant | None:
        ...

    @abstractmethod
    async def list_all(self, *, only_active: bool = False) -> list[Tenant]:
        ...
