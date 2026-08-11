"""Helpers for in-memory / SQLAlchemy repository tenant scoping (RLS simulation)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, false
from sqlalchemy.sql import Select

from src.shared.infrastructure.tenant_context import get_current_tenant_id, get_rls_bypass


def matches_tenant_scope(tenant_id: UUID) -> bool:
    """In-memory scope: allow when unbound/bypass, else require matching tenant."""
    if get_rls_bypass():
        return True
    current = get_current_tenant_id()
    return current is None or tenant_id == current


def apply_tenant_scope(stmt: Select, column: ColumnElement[UUID]) -> Select:
    """Add app-layer tenant_id filter (defense-in-depth beside Postgres RLS)."""
    if get_rls_bypass():
        return stmt
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        return stmt.where(false())
    return stmt.where(column == tenant_id)
