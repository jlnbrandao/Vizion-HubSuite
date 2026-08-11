"""Permission read models / DTOs returned by query handlers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class PermissionDto:
    id: UUID
    code: str
    resource: str
    action: str
    name: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class PermissionsExistResult:
    all_exist: bool
    missing_ids: frozenset[UUID]
