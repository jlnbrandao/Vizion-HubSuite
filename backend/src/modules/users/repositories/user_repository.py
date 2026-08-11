"""User repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.modules.users.entities.user import User
from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.username import Username
from src.shared.domain.repository import Repository


class UserRepository(Repository[User], ABC):
    @abstractmethod
    async def get_by_email(self, email: Email) -> User | None:
        ...

    @abstractmethod
    async def get_by_username(self, username: Username) -> User | None:
        ...

    @abstractmethod
    async def list_all(self, *, only_active: bool = False) -> list[User]:
        ...

    @abstractmethod
    async def exists_by_email(self, email: Email) -> bool:
        ...

    @abstractmethod
    async def exists_by_username(self, username: Username) -> bool:
        ...

    @abstractmethod
    async def count(self, *, only_active: bool = False) -> int:
        ...
