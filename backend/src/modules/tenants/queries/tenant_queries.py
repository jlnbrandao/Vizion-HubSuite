"""Read queries for Tenants module."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.shared.application.query import Query


@dataclass(frozen=True, kw_only=True)
class GetTenantBySlugQuery(Query):
    slug: str


@dataclass(frozen=True, kw_only=True)
class GetTenantByIdQuery(Query):
    tenant_id: UUID


@dataclass(frozen=True, kw_only=True)
class ListTenantsQuery(Query):
    only_active: bool = False
