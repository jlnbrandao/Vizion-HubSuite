"""PermissionCode — stable identifier for a permission.

Two shapes are accepted during the namespace migration:

  resource.action           legacy, e.g. users.create
  service.resource.action   canonical, e.g. iam.users.create

Legacy codes keep working until the aliases are dropped in a later, explicit step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject

_SEGMENT = r"[a-z][a-z0-9_]*"
_CODE_PATTERN = re.compile(rf"^{_SEGMENT}\.{_SEGMENT}(\.{_SEGMENT})?$")


@dataclass(frozen=True)
class PermissionCode(ValueObject):
    value: str

    def _validate(self) -> None:
        if not _CODE_PATTERN.match(self.value):
            raise ValueError(
                "Permission code must match 'resource.action' or "
                "'service.resource.action' (lowercase, underscore allowed), "
                "e.g. users.create or iam.users.create"
            )

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value.strip().lower())

    @property
    def segments(self) -> tuple[str, ...]:
        return tuple(self.value.split("."))

    @property
    def is_namespaced(self) -> bool:
        return len(self.segments) == 3

    @property
    def service(self) -> str | None:
        """Service namespace, or None for a legacy two-part code."""
        parts = self.segments
        return parts[0] if len(parts) == 3 else None

    @property
    def resource(self) -> str:
        parts = self.segments
        return parts[1] if len(parts) == 3 else parts[0]

    @property
    def action(self) -> str:
        return self.segments[-1]
