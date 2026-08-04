"""GetDashboard query — carries AuthZ context from the API layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.shared.application.query import Query


@dataclass(frozen=True, kw_only=True)
class GetDashboardQuery(Query):
    user_id: UUID
    email: str
    full_name: str
    role_ids: tuple[UUID, ...] = field(default_factory=tuple)
    role_names: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
