"""Helpers for in-memory repository tenant scoping (RLS simulation)."""

from __future__ import annotations

from uuid import UUID

from src.shared.infrastructure.tenant_context import get_current_tenant_id


def matches_tenant_scope(tenant_id: UUID) -> bool:
    current = get_current_tenant_id()
    return current is None or tenant_id == current
