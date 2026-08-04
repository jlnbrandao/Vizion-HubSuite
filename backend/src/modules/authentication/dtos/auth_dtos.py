"""Token pair DTO returned by login / refresh."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class TokenPairDto:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0  # seconds until access token expiry
    user_id: UUID | None = None
    email: str = ""
    full_name: str = ""


@dataclass(frozen=True, kw_only=True)
class RefreshSessionDto:
    """Data stored alongside a refresh token."""

    user_id: UUID
    email: str
    full_name: str
    role_ids: tuple[UUID, ...]
    created_at: datetime
