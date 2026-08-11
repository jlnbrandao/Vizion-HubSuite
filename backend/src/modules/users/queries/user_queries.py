"""Read queries for Users module."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.shared.application.query import Query


@dataclass(frozen=True, kw_only=True)
class GetUserByIdQuery(Query):
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class GetUserByEmailQuery(Query):
    """Used by Authentication module via QueryBus."""

    tenant_id: UUID
    email: str


@dataclass(frozen=True, kw_only=True)
class GetUserByUsernameQuery(Query):
    """Used by Authentication module via QueryBus (login by username)."""

    tenant_id: UUID
    username: str


@dataclass(frozen=True, kw_only=True)
class ListUsersQuery(Query):
    only_active: bool = False


@dataclass(frozen=True, kw_only=True)
class CountUsersQuery(Query):
    only_active: bool = False


@dataclass(frozen=True, kw_only=True)
class ResolveTenantAdminsQuery(Query):
    """Platform catalog: primary ADMIN user per tenant (via role name)."""

    tenant_ids: frozenset[UUID]
    role_name: str = "ADMIN"
    only_active: bool = True
