"""In-memory User repository for unit tests."""

from __future__ import annotations

from uuid import UUID

from src.modules.users.entities.user import User
from src.modules.users.repositories.user_repository import UserRepository
from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.username import Username
from src.shared.infrastructure.tenant_scope import matches_tenant_scope


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, User] = {}

    async def get_by_id(self, entity_id: UUID) -> User | None:
        user = self._items.get(entity_id)
        if user is None or not matches_tenant_scope(user.tenant_id):
            return None
        return user

    async def get_by_email(self, email: Email) -> User | None:
        return next(
            (
                u
                for u in self._items.values()
                if u.email == email and matches_tenant_scope(u.tenant_id)
            ),
            None,
        )

    async def get_by_username(self, username: Username) -> User | None:
        return next(
            (
                u
                for u in self._items.values()
                if u.username == username and matches_tenant_scope(u.tenant_id)
            ),
            None,
        )

    async def add(self, entity: User) -> None:
        self._items[entity.id] = entity

    async def update(self, entity: User) -> None:
        self._items[entity.id] = entity

    async def delete(self, entity: User) -> None:
        self._items.pop(entity.id, None)

    async def exists(self, entity_id: UUID) -> bool:
        return await self.get_by_id(entity_id) is not None

    async def exists_by_email(self, email: Email) -> bool:
        return any(
            u.email == email and matches_tenant_scope(u.tenant_id) for u in self._items.values()
        )

    async def exists_by_username(self, username: Username) -> bool:
        return any(
            u.username == username and matches_tenant_scope(u.tenant_id)
            for u in self._items.values()
        )

    async def list_all(self, *, only_active: bool = False) -> list[User]:
        items = list(self._items.values())
        items = [u for u in items if matches_tenant_scope(u.tenant_id)]
        if only_active:
            items = [u for u in items if u.is_active]
        return sorted(items, key=lambda u: u.username.value)

    async def count(self, *, only_active: bool = False) -> int:
        items = [u for u in self._items.values() if matches_tenant_scope(u.tenant_id)]
        if only_active:
            return sum(1 for u in items if u.is_active)
        return len(items)

    async def find_primary_by_role_name_for_tenants(
        self,
        *,
        tenant_ids: set[UUID],
        role_name: str,
        only_active: bool = True,
    ) -> dict[UUID, User]:
        """In-memory: resolve via optional ``role_names`` map ``{role_id: name}``."""
        role_names: dict[UUID, str] = getattr(self, "role_names", {})
        admin_role_ids = {
            role_id for role_id, name in role_names.items() if name == role_name
        }
        if not admin_role_ids:
            return {}

        by_tenant: dict[UUID, list[User]] = {}
        for user in self._items.values():
            if user.tenant_id not in tenant_ids:
                continue
            if not matches_tenant_scope(user.tenant_id):
                continue
            if only_active and not user.is_active:
                continue
            if not (user.role_ids & admin_role_ids):
                continue
            by_tenant.setdefault(user.tenant_id, []).append(user)

        return {
            tid: sorted(users, key=lambda u: u.created_at)[0]
            for tid, users in by_tenant.items()
            if users
        }
