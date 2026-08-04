"""Resolve effective roles + permission codes for AuthZ (gateway)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.shared.application.query import Query


@dataclass(frozen=True, kw_only=True)
class ResolveEffectiveAccessQuery(Query):
    role_ids: frozenset[UUID] = field(default_factory=frozenset)


@dataclass(frozen=True, kw_only=True)
class EffectiveAccessDto:
    role_names: frozenset[str] = field(default_factory=frozenset)
    permission_codes: frozenset[str] = field(default_factory=frozenset)
