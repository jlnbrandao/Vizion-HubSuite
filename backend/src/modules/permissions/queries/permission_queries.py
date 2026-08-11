"""Read queries for Permissions module (public contracts for other modules)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.shared.application.query import Query


@dataclass(frozen=True, kw_only=True)
class GetPermissionByIdQuery(Query):
    permission_id: UUID


@dataclass(frozen=True, kw_only=True)
class ListPermissionsQuery(Query):
    only_active: bool = False
    resource: str | None = None
    action: str | None = None


@dataclass(frozen=True, kw_only=True)
class CheckPermissionsExistQuery(Query):
    """Public contract — Roles module uses this via QueryBus (no internal imports)."""

    permission_ids: frozenset[UUID]


@dataclass(frozen=True, kw_only=True)
class GetPermissionsByIdsQuery(Query):
    """Public contract — AuthZ resolves permission codes from IDs."""

    permission_ids: frozenset[UUID]


@dataclass(frozen=True, kw_only=True)
class CountPermissionsQuery(Query):
    only_active: bool = False
