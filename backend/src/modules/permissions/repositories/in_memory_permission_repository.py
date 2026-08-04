"""In-memory Permission repository for unit tests."""

from __future__ import annotations

from uuid import UUID

from src.modules.permissions.entities.permission import Permission
from src.modules.permissions.repositories.permission_repository import PermissionRepository
from src.modules.permissions.value_objects.permission_code import PermissionCode


class InMemoryPermissionRepository(PermissionRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, Permission] = {}

    async def get_by_id(self, entity_id: UUID) -> Permission | None:
        return self._items.get(entity_id)

    async def get_by_code(self, code: PermissionCode) -> Permission | None:
        return next((p for p in self._items.values() if p.code == code), None)

    async def add(self, entity: Permission) -> None:
        self._items[entity.id] = entity

    async def update(self, entity: Permission) -> None:
        self._items[entity.id] = entity

    async def delete(self, entity: Permission) -> None:
        self._items.pop(entity.id, None)

    async def exists(self, entity_id: UUID) -> bool:
        return entity_id in self._items

    async def exists_by_code(self, code: PermissionCode) -> bool:
        return any(p.code == code for p in self._items.values())

    async def list_all(self, *, only_active: bool = False) -> list[Permission]:
        items = list(self._items.values())
        if only_active:
            items = [p for p in items if p.is_active]
        return sorted(items, key=lambda p: p.code.value)

    async def find_by_ids(self, ids: set[UUID]) -> list[Permission]:
        return [self._items[i] for i in ids if i in self._items]

    async def count(self, *, only_active: bool = False) -> int:
        items = self._items.values()
        if only_active:
            return sum(1 for p in items if p.is_active)
        return len(self._items)
