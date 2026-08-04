"""RefreshToken — opaque token identity (never a JWT)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Self

from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True)
class RefreshToken(ValueObject):
    value: str

    def _validate(self) -> None:
        if len(self.value) < 32:
            raise ValueError("Refresh token is too short")

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        return cls(value=value)

    @classmethod
    def generate(cls) -> Self:
        return cls(value=secrets.token_urlsafe(48))
