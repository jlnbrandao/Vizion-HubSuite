"""Permission repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.modules.permissions.entities.permission import Permission
from src.modules.permissions.value_objects.permission_code import PermissionCode
from src.shared.domain.repository import Repository


class PermissionRepository(Repository[Permission], ABC):
    @abstractmethod
    async def get_by_code(self, code: PermissionCode) -> Permission | None:
        ...

    @abstractmethod
    async def list_all(
        self,
        *,
        only_active: bool = False,
        service: str | None = None,
        resource: str | None = None,
        action: str | None = None,
    ) -> list[Permission]:
        ...

    @abstractmethod
    async def find_by_ids(self, ids: set[UUID]) -> list[Permission]:
        ...

    @abstractmethod
    async def exists_by_code(self, code: PermissionCode) -> bool:
        ...

    @abstractmethod
    async def count(self, *, only_active: bool = False) -> int:
        ...
