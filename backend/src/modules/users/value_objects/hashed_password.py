"""HashedPassword — never stores plain text. Created only via PasswordHasher."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True)
class HashedPassword(ValueObject):
    value: str

    def _validate(self) -> None:
        if not self.value or len(self.value) < 20:
            raise ValueError("Invalid hashed password")

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value)
