"""Read queries for Tenants module."""

from __future__ import annotations

from dataclasses import dataclass

from src.shared.application.query import Query


@dataclass(frozen=True, kw_only=True)
class GetTenantBySlugQuery(Query):
    slug: str
