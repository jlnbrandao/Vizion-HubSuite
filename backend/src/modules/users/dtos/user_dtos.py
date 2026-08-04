"""User read models / DTOs. Never expose hashed_password in public API DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class UserDto:
    id: UUID
    email: str
    full_name: str
    role_ids: tuple[UUID, ...] = field(default_factory=tuple)
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, kw_only=True)
class UserAuthDto:
    """Internal DTO for authentication — includes hashed password."""

    id: UUID
    email: str
    full_name: str
    hashed_password: str
    role_ids: tuple[UUID, ...] = field(default_factory=tuple)
    is_active: bool = True
