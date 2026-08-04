"""Role read models / DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class RoleDto:
    id: UUID
    name: str
    description: str
    permission_ids: tuple[UUID, ...] = field(default_factory=tuple)
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, kw_only=True)
class RolesExistResult:
    all_exist: bool
    missing_ids: frozenset[UUID]
