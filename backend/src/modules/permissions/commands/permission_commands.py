"""Write commands for Permissions module."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.shared.application.command import Command


@dataclass(frozen=True, kw_only=True)
class CreatePermissionCommand(Command):
    code: str
    name: str
    description: str = ""


@dataclass(frozen=True, kw_only=True)
class UpdatePermissionCommand(Command):
    permission_id: UUID
    name: str
    description: str = ""
    is_active: bool = True


@dataclass(frozen=True, kw_only=True)
class DeletePermissionCommand(Command):
    permission_id: UUID
