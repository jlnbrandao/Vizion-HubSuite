"""Role repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.modules.roles.entities.role import Role
from src.modules.roles.value_objects.role_name import RoleName
from src.shared.domain.repository import Repository


class RoleRepository(Repository[Role], ABC):
    @abstractmethod
    async def get_by_name(self, name: RoleName) -> Role | None:
        ...

    @abstractmethod
    async def list_all(self, *, only_active: bool = False) -> list[Role]:
        ...

    @abstractmethod
    async def exists_by_name(self, name: RoleName) -> bool:
        ...

    @abstractmethod
    async def find_by_ids(self, ids: set[UUID]) -> list[Role]:
        ...

    @abstractmethod
    async def count(self, *, only_active: bool = False) -> int:
        ...
