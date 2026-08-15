"""Read queries for permission bundles (public contract for AuthZ and Roles)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.shared.application.query import Query


@dataclass(frozen=True, kw_only=True)
class ResolveRoleBundleCodesQuery(Query):
    """Permission codes the given roles inherit from bundles."""

    role_ids: frozenset[UUID]
