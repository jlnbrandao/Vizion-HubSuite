"""CurrentUser — authenticated principal for the request (AuthN + AuthZ context)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.shared.infrastructure.security.permission_codes import PermissionCode


@dataclass(frozen=True, kw_only=True)
class CurrentUser:
    id: UUID
    email: str
    full_name: str
    tenant_id: UUID
    tenant_slug: str
    tenant_name: str = ""
    role_ids: tuple[UUID, ...] = field(default_factory=tuple)
    role_names: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)

    def has_permission(self, code: str) -> bool:
        """Namespaced and legacy forms of a code are equivalent."""
        if code in self.permissions:
            return True
        return bool(self.permissions & PermissionCode.aliases(code))

    def has_any_permission(self, *codes: str) -> bool:
        return any(self.has_permission(code) for code in codes)

    def has_all_permissions(self, *codes: str) -> bool:
        return all(self.has_permission(code) for code in codes)

    def has_role(self, name: str) -> bool:
        return name.upper() in self.role_names

    def has_any_role(self, *names: str) -> bool:
        wanted = {n.upper() for n in names}
        return bool(self.role_names & wanted)
