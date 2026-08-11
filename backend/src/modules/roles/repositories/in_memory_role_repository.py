"""In-memory Role repository for unit tests."""

from __future__ import annotations

from uuid import UUID

from src.modules.roles.entities.role import Role
from src.modules.roles.repositories.role_repository import RoleRepository
from src.modules.roles.value_objects.role_name import RoleName
from src.shared.infrastructure.tenant_scope import matches_tenant_scope


class InMemoryRoleRepository(RoleRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, Role] = {}

    async def get_by_id(self, entity_id: UUID) -> Role | None:
        role = self._items.get(entity_id)
        if role is None or not matches_tenant_scope(role.tenant_id):
            return None
        return role

    async def get_by_name(self, name: RoleName) -> Role | None:
        return next(
            (
                r
                for r in self._items.values()
                if r.name == name and matches_tenant_scope(r.tenant_id)
            ),
            None,
        )

    async def add(self, entity: Role) -> None:
        self._items[entity.id] = entity

    async def update(self, entity: Role) -> None:
        self._items[entity.id] = entity

    async def delete(self, entity: Role) -> None:
        self._items.pop(entity.id, None)

    async def exists(self, entity_id: UUID) -> bool:
        return entity_id in self._items

    async def exists_by_name(self, name: RoleName) -> bool:
        return any(
            r.name == name and matches_tenant_scope(r.tenant_id) for r in self._items.values()
        )

    async def list_all(self, *, only_active: bool = False) -> list[Role]:
        items = list(self._items.values())
        items = [r for r in items if matches_tenant_scope(r.tenant_id)]
        if only_active:
            items = [r for r in items if r.is_active]
        return sorted(items, key=lambda r: r.name.value)

    async def find_by_ids(self, ids: set[UUID]) -> list[Role]:
        return [self._items[i] for i in ids if i in self._items]

    async def count(self, *, only_active: bool = False) -> int:
        items = self._items.values()
        if only_active:
            return sum(1 for r in items if r.is_active)
        return len(self._items)
