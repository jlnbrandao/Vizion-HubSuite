"""Domain events for the Roles module."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class RoleCreatedEvent(DomainEvent):
    name: str = ""


@dataclass(frozen=True, kw_only=True)
class RoleUpdatedEvent(DomainEvent):
    name: str = ""


@dataclass(frozen=True, kw_only=True)
class RoleDeletedEvent(DomainEvent):
    name: str = ""


@dataclass(frozen=True, kw_only=True)
class PermissionsAssignedToRoleEvent(DomainEvent):
    role_name: str = ""
    permission_ids: tuple[UUID, ...] = field(default_factory=tuple)


@dataclass(frozen=True, kw_only=True)
class PermissionsRevokedFromRoleEvent(DomainEvent):
    role_name: str = ""
    permission_ids: tuple[UUID, ...] = field(default_factory=tuple)
