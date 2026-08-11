"""Write commands for Users module."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.shared.application.command import Command


@dataclass(frozen=True, kw_only=True)
class CreateUserCommand(Command):
    tenant_id: UUID
    email: str
    username: str
    full_name: str
    password: str
    role_ids: frozenset[UUID] = field(default_factory=frozenset)


@dataclass(frozen=True, kw_only=True)
class UpdateUserCommand(Command):
    user_id: UUID
    username: str
    full_name: str
    is_active: bool = True


@dataclass(frozen=True, kw_only=True)
class ChangeUserPasswordCommand(Command):
    user_id: UUID
    new_password: str


@dataclass(frozen=True, kw_only=True)
class DeleteUserCommand(Command):
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class AssignRolesToUserCommand(Command):
    user_id: UUID
    role_ids: frozenset[UUID] = field(default_factory=frozenset)


@dataclass(frozen=True, kw_only=True)
class RevokeRolesFromUserCommand(Command):
    user_id: UUID
    role_ids: frozenset[UUID] = field(default_factory=frozenset)


@dataclass(frozen=True, kw_only=True)
class ReplaceUserRolesCommand(Command):
    user_id: UUID
    role_ids: frozenset[UUID] = field(default_factory=frozenset)
