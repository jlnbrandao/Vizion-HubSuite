"""In-memory Tenant repository for unit tests."""

from __future__ import annotations

from uuid import UUID

from src.modules.tenants.entities.tenant import Tenant
from src.modules.tenants.repositories.tenant_repository import TenantRepository
from src.modules.tenants.value_objects.tenant_slug import TenantSlug


class InMemoryTenantRepository(TenantRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, Tenant] = {}

    async def get_by_id(self, entity_id: UUID) -> Tenant | None:
        return self._items.get(entity_id)

    async def get_by_slug(self, slug: TenantSlug) -> Tenant | None:
        return next((t for t in self._items.values() if t.slug == slug), None)

    async def list_all(self, *, only_active: bool = False) -> list[Tenant]:
        items = list(self._items.values())
        if only_active:
            items = [t for t in items if t.is_active]
        return sorted(items, key=lambda t: t.slug.value)

    async def add(self, entity: Tenant) -> None:
        self._items[entity.id] = entity

    async def update(self, entity: Tenant) -> None:
        self._items[entity.id] = entity

    async def delete(self, entity: Tenant) -> None:
        self._items.pop(entity.id, None)

    async def exists(self, entity_id: UUID) -> bool:
        return entity_id in self._items
