"""Domain events for the Permissions module."""

from __future__ import annotations

from dataclasses import dataclass

from src.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PermissionCreatedEvent(DomainEvent):
    code: str = ""
    name: str = ""


@dataclass(frozen=True, kw_only=True)
class PermissionUpdatedEvent(DomainEvent):
    code: str = ""
    name: str = ""


@dataclass(frozen=True, kw_only=True)
class PermissionDeletedEvent(DomainEvent):
    code: str = ""
