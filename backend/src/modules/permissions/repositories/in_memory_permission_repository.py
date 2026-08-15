"""In-memory Permission repository for unit tests."""

from __future__ import annotations

from uuid import UUID

from src.modules.permissions.entities.permission import Permission
from src.modules.permissions.repositories.permission_repository import PermissionRepository
from src.modules.permissions.value_objects.permission_code import PermissionCode
from src.shared.infrastructure.security.permission_codes import (
    PermissionCode as PermissionCatalog,
)
from src.shared.infrastructure.tenant_scope import matches_tenant_scope


class InMemoryPermissionRepository(PermissionRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, Permission] = {}

    async def get_by_id(self, entity_id: UUID) -> Permission | None:
        permission = self._items.get(entity_id)
        if permission is None or not matches_tenant_scope(permission.tenant_id):
            return None
        return permission

    async def get_by_code(self, code: PermissionCode) -> Permission | None:
        return next(
            (
                p
                for p in self._items.values()
                if p.code == code and matches_tenant_scope(p.tenant_id)
            ),
            None,
        )

    async def add(self, entity: Permission) -> None:
        self._items[entity.id] = entity

    async def update(self, entity: Permission) -> None:
        self._items[entity.id] = entity

    async def delete(self, entity: Permission) -> None:
        self._items.pop(entity.id, None)

    async def exists(self, entity_id: UUID) -> bool:
        return entity_id in self._items

    async def exists_by_code(self, code: PermissionCode) -> bool:
        return any(
            p.code == code and matches_tenant_scope(p.tenant_id) for p in self._items.values()
        )

    async def list_all(
        self,
        *,
        only_active: bool = False,
        service: str | None = None,
        resource: str | None = None,
        action: str | None = None,
    ) -> list[Permission]:
        items = list(self._items.values())
        items = [p for p in items if matches_tenant_scope(p.tenant_id)]
        if only_active:
            items = [p for p in items if p.is_active]
        if service:
            items = [
                p
                for p in items
                if (p.code.service or PermissionCatalog.service_of(p.code.value)) == service
            ]
        if resource:
            items = [p for p in items if p.code.resource == resource]
        if action:
            items = [p for p in items if p.code.action == action]
        return sorted(items, key=lambda p: p.code.value)

    async def find_by_ids(self, ids: set[UUID]) -> list[Permission]:
        return [self._items[i] for i in ids if i in self._items]

    async def count(self, *, only_active: bool = False) -> int:
        items = self._items.values()
        if only_active:
            return sum(1 for p in items if p.is_active)
        return len(self._items)
