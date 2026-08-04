"""Password hashing port — implementation lives in infrastructure (bcrypt)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.plain_password import PlainPassword


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, plain: PlainPassword) -> HashedPassword:
        ...

    @abstractmethod
    def verify(self, plain: PlainPassword, hashed: HashedPassword) -> bool:
        ...
