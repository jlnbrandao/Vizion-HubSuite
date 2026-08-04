"""Domain events for the Users module."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserCreatedEvent(DomainEvent):
    email: str = ""


@dataclass(frozen=True, kw_only=True)
class UserUpdatedEvent(DomainEvent):
    email: str = ""


@dataclass(frozen=True, kw_only=True)
class UserDeletedEvent(DomainEvent):
    email: str = ""


@dataclass(frozen=True, kw_only=True)
class UserPasswordChangedEvent(DomainEvent):
    email: str = ""


@dataclass(frozen=True, kw_only=True)
class RolesAssignedToUserEvent(DomainEvent):
    email: str = ""
    role_ids: tuple[UUID, ...] = field(default_factory=tuple)


@dataclass(frozen=True, kw_only=True)
class RolesRevokedFromUserEvent(DomainEvent):
    email: str = ""
    role_ids: tuple[UUID, ...] = field(default_factory=tuple)
