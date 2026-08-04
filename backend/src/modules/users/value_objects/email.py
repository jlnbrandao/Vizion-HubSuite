"""Email value object."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject

_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@dataclass(frozen=True)
class Email(ValueObject):
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.strip().lower())
        super().__post_init__()

    def _validate(self) -> None:
        if not _EMAIL_PATTERN.match(self.value):
            raise ValueError(f"Invalid email address: {self.value}")
        if len(self.value) > 255:
            raise ValueError("Email cannot exceed 255 characters")

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value)
