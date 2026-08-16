from __future__ import annotations

from contextvars import ContextVar, Token
from uuid import UUID

from openvizion.kernel.identity import TenantInfo

_tenant: ContextVar[TenantInfo | None] = ContextVar("tracking_tenant", default=None)


def get_tenant() -> TenantInfo | None:
    return _tenant.get()


def require_tenant() -> TenantInfo:
    tenant = _tenant.get()
    if tenant is None:
        raise RuntimeError("No tenant context")
    return tenant


def bind_tenant(tenant: TenantInfo) -> Token[TenantInfo | None]:
    return _tenant.set(tenant)


def unbind_tenant(token: Token[TenantInfo | None]) -> None:
    _tenant.reset(token)


def extract_slug(host: str | None) -> str:
    if not host:
        raise ValueError("Missing Host header")
    hostname = host.split(":")[0].strip().lower()
    if not hostname:
        raise ValueError("Invalid Host header")
    if hostname in {"localhost", "127.0.0.1"}:
        return "demo"
    return hostname.split(".")[0]
