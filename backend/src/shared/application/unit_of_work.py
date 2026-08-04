"""Unit of Work — transactional boundary for a single use case.

Responsibilities:
1. Own one SQLAlchemy AsyncSession (or equivalent).
2. Commit / rollback atomically.
3. Collect Domain Events from tracked Aggregate Roots.
4. Publish events via Event Bus *after* a successful commit.

Handlers receive a UoW via DI and never manage transactions themselves.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from src.shared.domain.aggregate_root import AggregateRoot
from src.shared.domain.domain_event import DomainEvent


class UnitOfWork(ABC):
    @abstractmethod
    async def __aenter__(self) -> Self:
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Persist changes and publish collected domain events."""

    @abstractmethod
    async def rollback(self) -> None:
        """Discard all pending changes."""

    @abstractmethod
    def track(self, aggregate: AggregateRoot) -> None:
        """Register an aggregate so its events are collected on commit."""

    @abstractmethod
    def collect_events(self) -> list[DomainEvent]:
        """Pull events from all tracked aggregates."""
