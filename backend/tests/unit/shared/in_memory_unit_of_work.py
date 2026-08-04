"""In-memory Unit of Work for unit tests (no database)."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from src.shared.application.event_bus import EventBus
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.domain.aggregate_root import AggregateRoot
from src.shared.domain.domain_event import DomainEvent


class InMemoryUnitOfWork(UnitOfWork):
    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus or EventBus()
        self._tracked: list[AggregateRoot] = []
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        self._tracked = []
        self.committed = False
        self.rolled_back = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    def track(self, aggregate: AggregateRoot) -> None:
        if aggregate not in self._tracked:
            self._tracked.append(aggregate)

    def collect_events(self) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for aggregate in self._tracked:
            events.extend(aggregate.pull_domain_events())
        return events

    async def commit(self) -> None:
        events = self.collect_events()
        self.committed = True
        await self._event_bus.publish_many(events)

    async def rollback(self) -> None:
        self.rolled_back = True
        self._tracked = []
