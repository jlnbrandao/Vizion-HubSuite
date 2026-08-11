"""Username value object — unique public handle (also used for login)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject

# Lowercase letters, digits; specials limited to . - _
_USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")


@dataclass(frozen=True)
class Username(ValueObject):
    value: str

    def _validate(self) -> None:
        if not _USERNAME_PATTERN.match(self.value):
            raise ValueError(
                "Username must be 3–32 lowercase chars: letters, digits, "
                "and only '.', '-' or '_' as special characters"
            )

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value.strip().lower())
