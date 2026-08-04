"""Read queries for Roles module (includes public contracts for other modules)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.shared.application.query import Query


@dataclass(frozen=True, kw_only=True)
class GetRoleByIdQuery(Query):
    role_id: UUID


@dataclass(frozen=True, kw_only=True)
class ListRolesQuery(Query):
    only_active: bool = False


@dataclass(frozen=True, kw_only=True)
class CheckRolesExistQuery(Query):
    """Public contract — Users module uses this via QueryBus."""

    role_ids: frozenset[UUID]


@dataclass(frozen=True, kw_only=True)
class GetRolesByIdsQuery(Query):
    """Public contract — AuthZ resolves role names + permission IDs."""

    role_ids: frozenset[UUID]


@dataclass(frozen=True, kw_only=True)
class CountRolesQuery(Query):
    only_active: bool = False
