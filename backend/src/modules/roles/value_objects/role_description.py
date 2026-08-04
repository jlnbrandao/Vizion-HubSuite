"""RoleDescription — optional descriptive text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True)
class RoleDescription(ValueObject):
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.strip())
        super().__post_init__()

    def _validate(self) -> None:
        if len(self.value) > 500:
            raise ValueError("Role description cannot exceed 500 characters")

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value)
