"""Tenant Aggregate Root."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.modules.tenants.value_objects.tenant_slug import TenantSlug
from src.shared.domain.aggregate_root import AggregateRoot


@dataclass(eq=False, kw_only=True)
class Tenant(AggregateRoot):
    slug: TenantSlug
    name: str
    is_active: bool = True

    @classmethod
    def create(cls, *, slug: TenantSlug, name: str, tenant_id: UUID | None = None) -> Tenant:
        if tenant_id is None:
            return cls(slug=slug, name=name.strip())
        return cls(id=tenant_id, slug=slug, name=name.strip())

    def rename(self, name: str) -> None:
        cleaned = name.strip()
        if self.name == cleaned:
            return
        self.name = cleaned
        self.touch()
