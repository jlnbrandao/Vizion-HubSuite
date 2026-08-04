"""Write commands for Roles module."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.shared.application.command import Command


@dataclass(frozen=True, kw_only=True)
class CreateRoleCommand(Command):
    name: str
    description: str = ""


@dataclass(frozen=True, kw_only=True)
class UpdateRoleCommand(Command):
    role_id: UUID
    description: str = ""
    is_active: bool = True


@dataclass(frozen=True, kw_only=True)
class DeleteRoleCommand(Command):
    role_id: UUID


@dataclass(frozen=True, kw_only=True)
class AssignPermissionsToRoleCommand(Command):
    role_id: UUID
    permission_ids: frozenset[UUID] = field(default_factory=frozenset)


@dataclass(frozen=True, kw_only=True)
class RevokePermissionsFromRoleCommand(Command):
    role_id: UUID
    permission_ids: frozenset[UUID] = field(default_factory=frozenset)


@dataclass(frozen=True, kw_only=True)
class ReplaceRolePermissionsCommand(Command):
    role_id: UUID
    permission_ids: frozenset[UUID] = field(default_factory=frozenset)
