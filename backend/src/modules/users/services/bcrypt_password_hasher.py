"""Bcrypt password hasher — infrastructure adapter for PasswordHasher port."""

from __future__ import annotations

from passlib.context import CryptContext

from src.modules.users.services.password_hasher import PasswordHasher
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.plain_password import PlainPassword

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, plain: PlainPassword) -> HashedPassword:
        return HashedPassword(value=_pwd_context.hash(plain.value))

    def verify(self, plain: PlainPassword, hashed: HashedPassword) -> bool:
        return _pwd_context.verify(plain.value, hashed.value)
