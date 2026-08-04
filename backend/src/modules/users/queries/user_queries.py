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
    """Used by Authentication module in later stages via QueryBus."""

    email: str


@dataclass(frozen=True, kw_only=True)
class ListUsersQuery(Query):
    only_active: bool = False


@dataclass(frozen=True, kw_only=True)
class CountUsersQuery(Query):
    only_active: bool = False
