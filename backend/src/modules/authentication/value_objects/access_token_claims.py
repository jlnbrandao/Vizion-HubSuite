"""AccessTokenClaims — payload carried inside the JWT.

Deliberately minimal: identity, tenant context and validation metadata only.
Profile data (email, name) and authorization data (roles, permissions) are served
by `GET /auth/me` so the token carries no PII and no stale access decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Self
from uuid import UUID

from src.shared.domain.value_object import ValueObject


@dataclass(frozen=True)
class AccessTokenClaims(ValueObject):
    user_id: UUID
    tenant_id: UUID
    tenant_slug: str
    credentials_version: int = 0
    amr: tuple[str, ...] = field(default_factory=tuple)
    acr: str | None = None
    sid: UUID | None = None
    token_use: str = "access"
    exp: datetime | None = None
    iat: datetime | None = None

    def _validate(self) -> None:
        if not self.tenant_slug:
            raise ValueError("Access token claims require a tenant_slug")
        if self.credentials_version < 0:
            raise ValueError("credentials_version cannot be negative")

    def to_primitive(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "sub": str(self.user_id),
            "tenant_id": str(self.tenant_id),
            "tenant_slug": self.tenant_slug,
            "cv": self.credentials_version,
            "amr": list(self.amr),
            "token_use": self.token_use,
            "exp": int(self.exp.timestamp()) if self.exp else None,
            "iat": int(self.iat.timestamp()) if self.iat else None,
        }
        if self.acr is not None:
            payload["acr"] = self.acr
        if self.sid is not None:
            payload["sid"] = str(self.sid)
        return payload

    @classmethod
    def from_primitive(cls, value: dict[str, object]) -> Self:
        amr_raw = value.get("amr") or []
        if not isinstance(amr_raw, list):
            amr_raw = []
        iat_raw = value.get("iat")
        exp_raw = value.get("exp")
        cv_raw = value.get("cv", 0)
        sid_raw = value.get("sid")
        acr_raw = value.get("acr")
        return cls(
            user_id=UUID(str(value["sub"])),
            tenant_id=UUID(str(value["tenant_id"])),
            tenant_slug=str(value["tenant_slug"]),
            credentials_version=int(cv_raw) if cv_raw is not None else 0,
            amr=tuple(str(item) for item in amr_raw),
            acr=str(acr_raw) if acr_raw is not None else None,
            sid=UUID(str(sid_raw)) if sid_raw else None,
            token_use=str(value.get("token_use") or "access"),
            iat=(
                datetime.fromtimestamp(int(iat_raw), UTC)
                if iat_raw is not None
                else None
            ),
            exp=(
                datetime.fromtimestamp(int(exp_raw), UTC)
                if exp_raw is not None
                else None
            ),
        )
