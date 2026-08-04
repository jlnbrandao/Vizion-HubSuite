"""RoleName — unique role identifier (e.g. ADMIN)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject

_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


@dataclass(frozen=True)
class RoleName(ValueObject):
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.strip().upper())
        super().__post_init__()

    def _validate(self) -> None:
        if not _NAME_PATTERN.match(self.value):
            raise ValueError(
                "Role name must be uppercase alphanumeric/underscore, 2-64 chars "
                "(e.g. ADMIN, MANAGER)"
            )

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value)
