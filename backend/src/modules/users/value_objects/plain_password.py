"""PlainPassword — validated at the application boundary, never persisted."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True)
class PlainPassword(ValueObject):
    value: str

    def _validate(self) -> None:
        if len(self.value) < 8:
            raise ValueError("Password must have at least 8 characters")
        if len(self.value) > 128:
            raise ValueError("Password cannot exceed 128 characters")
        if self.value.isspace():
            raise ValueError("Password cannot be blank")

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value)
