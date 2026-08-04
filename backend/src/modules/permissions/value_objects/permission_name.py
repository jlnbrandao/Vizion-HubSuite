"""PermissionName — human-readable label."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True)
class PermissionName(ValueObject):
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.strip())
        super().__post_init__()

    def _validate(self) -> None:
        if not self.value:
            raise ValueError("Permission name cannot be empty")
        if len(self.value) > 120:
            raise ValueError("Permission name cannot exceed 120 characters")

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value)
