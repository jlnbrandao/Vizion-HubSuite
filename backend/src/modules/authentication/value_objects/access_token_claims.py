"""AccessTokenClaims — payload carried inside the JWT."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Self
from uuid import UUID

from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True)
class AccessTokenClaims(ValueObject):
    user_id: UUID
    email: str
    full_name: str
    role_ids: tuple[UUID, ...] = field(default_factory=tuple)
    exp: datetime | None = None
    iat: datetime | None = None

    def _validate(self) -> None:
        if not self.email:
            raise ValueError("Access token claims require an email")

    def to_primitive(self) -> dict[str, object]:
        return {
            "sub": str(self.user_id),
            "email": self.email,
            "full_name": self.full_name,
            "role_ids": [str(rid) for rid in self.role_ids],
            "exp": int(self.exp.timestamp()) if self.exp else None,
            "iat": int(self.iat.timestamp()) if self.iat else None,
        }

    @classmethod
    def from_primitive(cls, value: dict[str, object]) -> Self:
        role_raw = value.get("role_ids") or []
        if not isinstance(role_raw, list):
            role_raw = []
        return cls(
            user_id=UUID(str(value["sub"])),
            email=str(value["email"]),
            full_name=str(value.get("full_name", "")),
            role_ids=tuple(UUID(str(rid)) for rid in role_raw),
        )
