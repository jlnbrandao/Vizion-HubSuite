"""CurrentUser — authenticated principal for the request (AuthN + AuthZ context)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class CurrentUser:
    id: UUID
    email: str
    full_name: str
    role_ids: tuple[UUID, ...] = field(default_factory=tuple)
    role_names: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(code in self.permissions for code in codes)

    def has_all_permissions(self, *codes: str) -> bool:
        return all(code in self.permissions for code in codes)

    def has_role(self, name: str) -> bool:
        return name.upper() in self.role_names

    def has_any_role(self, *names: str) -> bool:
        wanted = {n.upper() for n in names}
        return bool(self.role_names & wanted)
