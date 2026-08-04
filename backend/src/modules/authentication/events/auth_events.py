"""Authentication domain events."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserLoggedInEvent(DomainEvent):
    user_id: UUID | None = None
    email: str = ""


@dataclass(frozen=True, kw_only=True)
class UserLoggedOutEvent(DomainEvent):
    user_id: UUID | None = None
    email: str = ""


@dataclass(frozen=True, kw_only=True)
class TokenRefreshedEvent(DomainEvent):
    user_id: UUID | None = None
    email: str = ""
