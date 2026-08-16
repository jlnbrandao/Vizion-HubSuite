"""Authenticated principal and tenant identity — shared by every product kernel."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class TenantInfo:
    id: UUID
    slug: str
    name: str
    is_active: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class Principal:
    """Identity derived from the authenticated session — never from the request body."""

    id: UUID
    email: str
    full_name: str
    tenant_id: UUID
    tenant_slug: str
    tenant_name: str = ""
    role_names: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(code in self.permissions for code in codes)

    def has_role(self, name: str) -> bool:
        return name.upper() in {role.upper() for role in self.role_names}
