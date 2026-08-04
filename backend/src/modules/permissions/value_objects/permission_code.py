"""PermissionCode — unique stable identifier (e.g. users.create)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class PermissionCode(ValueObject):
    value: str

    def _validate(self) -> None:
        if not _CODE_PATTERN.match(self.value):
            raise ValueError(
                "Permission code must match 'resource.action' "
                "(lowercase, underscore allowed), e.g. users.create"
            )

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value.strip().lower())

    @property
    def resource(self) -> str:
        return self.value.split(".", 1)[0]

    @property
    def action(self) -> str:
        return self.value.split(".", 1)[1]
