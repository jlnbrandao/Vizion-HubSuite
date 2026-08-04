"""Bcrypt password hasher — infrastructure adapter for PasswordHasher port."""

from __future__ import annotations

import bcrypt

from src.modules.users.services.password_hasher import PasswordHasher
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.plain_password import PlainPassword


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, plain: PlainPassword) -> HashedPassword:
        hashed = bcrypt.hashpw(plain.value.encode("utf-8"), bcrypt.gensalt())
        return HashedPassword(value=hashed.decode("utf-8"))

    def verify(self, plain: PlainPassword, hashed: HashedPassword) -> bool:
        return bcrypt.checkpw(
            plain.value.encode("utf-8"),
            hashed.value.encode("utf-8"),
        )
