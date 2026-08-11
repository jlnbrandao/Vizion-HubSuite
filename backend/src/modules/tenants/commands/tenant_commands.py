"""Write commands for Tenants module."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.shared.application.command import Command


@dataclass(frozen=True, kw_only=True)
class UpsertTenantCommand(Command):
    slug: str
    name: str
    tenant_id: UUID | None = None
