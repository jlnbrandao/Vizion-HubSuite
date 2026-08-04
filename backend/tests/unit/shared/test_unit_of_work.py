"""Unit tests for in-memory Unit of Work behavior (event collection + publish order)."""

from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import Self
from uuid import uuid4

import pytest

from src.shared.application.event_bus import EventBus
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.domain.aggregate_root import AggregateRoot
from src.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ItemCreated(DomainEvent):
    label: str = ""


@dataclass(eq=False, kw_only=True)
class Item(AggregateRoot):
    label: str = ""

    @classmethod
    def create(cls, label: str) -> Item:
        item = cls(id=uuid4(), label=label)
        item.raise_event(ItemCreated(aggregate_id=item.id, label=label))
        return item


class InMemoryUnitOfWork(UnitOfWork):
    """Test double — no database; still honors commit → publish contract."""

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
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


@pytest.mark.asyncio
async def test_uow_publishes_events_only_after_commit() -> None:
    published: list[DomainEvent] = []
    bus = EventBus()

    async def capture(event: DomainEvent) -> None:
        published.append(event)

    bus.subscribe(ItemCreated, capture)

    async with InMemoryUnitOfWork(bus) as uow:
        item = Item.create("widget")
        uow.track(item)
        assert published == []
        await uow.commit()

    assert len(published) == 1
    assert isinstance(published[0], ItemCreated)
    assert published[0].label == "widget"


@pytest.mark.asyncio
async def test_uow_rollback_on_exception() -> None:
    bus = EventBus()
    uow = InMemoryUnitOfWork(bus)

    with pytest.raises(RuntimeError, match="boom"):
        async with uow:
            uow.track(Item.create("x"))
            raise RuntimeError("boom")

    assert uow.rolled_back is True
    assert uow.committed is False
