"""Request-scoped tenant context (ContextVar) for RLS GUC wiring."""

from __future__ import annotations

from contextvars import ContextVar, Token
from uuid import UUID

_tenant_id_ctx: ContextVar[UUID | None] = ContextVar("current_tenant_id", default=None)
_tenant_slug_ctx: ContextVar[str | None] = ContextVar("current_tenant_slug", default=None)
_tenant_name_ctx: ContextVar[str | None] = ContextVar("current_tenant_name", default=None)
_rls_bypass_ctx: ContextVar[bool] = ContextVar("rls_bypass", default=False)


def get_current_tenant_id() -> UUID | None:
    return _tenant_id_ctx.get()


def get_current_tenant_slug() -> str | None:
    return _tenant_slug_ctx.get()


def get_current_tenant_name() -> str | None:
    return _tenant_name_ctx.get()


def get_rls_bypass() -> bool:
    return _rls_bypass_ctx.get()


def require_current_tenant_id() -> UUID:
    tenant_id = _tenant_id_ctx.get()
    if tenant_id is None:
        raise RuntimeError("No active tenant context. Resolve tenant from Host first.")
    return tenant_id


def bind_tenant(
    tenant_id: UUID,
    *,
    slug: str | None = None,
    name: str | None = None,
) -> tuple[Token[UUID | None], Token[str | None], Token[str | None]]:
    id_token = _tenant_id_ctx.set(tenant_id)
    slug_token = _tenant_slug_ctx.set(slug)
    name_token = _tenant_name_ctx.set(name)
    return id_token, slug_token, name_token


def unbind_tenant(
    id_token: Token[UUID | None],
    slug_token: Token[str | None],
    name_token: Token[str | None],
) -> None:
    _tenant_id_ctx.reset(id_token)
    _tenant_slug_ctx.reset(slug_token)
    _tenant_name_ctx.reset(name_token)


def bind_rls_bypass(enabled: bool) -> Token[bool]:
    return _rls_bypass_ctx.set(enabled)


def unbind_rls_bypass(token: Token[bool]) -> None:
    _rls_bypass_ctx.reset(token)
