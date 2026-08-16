"""AuthorizationProvider — RBAC decisions without coupling to Hub IAM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from openvizion.kernel.identity import Principal


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    stage: str = "rbac"

    @property
    def denied(self) -> bool:
        return not self.allowed


class AuthorizationProvider(Protocol):
    async def authorize(
        self,
        principal: Principal,
        action: str,
        *,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
    ) -> AuthorizationDecision: ...
