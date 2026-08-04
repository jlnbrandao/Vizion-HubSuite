"""FullName value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True)
class FullName(ValueObject):
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", " ".join(self.value.split()))
        super().__post_init__()

    def _validate(self) -> None:
        if len(self.value) < 2:
            raise ValueError("Full name must have at least 2 characters")
        if len(self.value) > 150:
            raise ValueError("Full name cannot exceed 150 characters")

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value)
