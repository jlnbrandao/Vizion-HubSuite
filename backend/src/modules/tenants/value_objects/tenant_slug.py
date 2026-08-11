"""TenantSlug — lowercase DNS-like identifier (e.g. bigbang)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject

_SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$")


@dataclass(frozen=True)
class TenantSlug(ValueObject):
    value: str

    def _validate(self) -> None:
        if not _SLUG_PATTERN.match(self.value):
            raise ValueError(
                "Tenant slug must be 1–64 lowercase letters, digits, or hyphens; "
                "must start and end with a letter or digit"
            )

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value.strip().lower())
