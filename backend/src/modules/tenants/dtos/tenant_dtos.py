"""Tenant read models / DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class TenantDto:
    id: UUID
    slug: str
    name: str
    is_active: bool = True
