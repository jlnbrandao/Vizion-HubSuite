"""In-process Event Bus.

Subscribers react to Domain Events after a successful Unit of Work commit.
Multiple handlers can listen to the same event (fan-out: Audit, Logs, Notifications).

This implementation is synchronous/async in-process. A future adapter can push
to Redis Streams / RabbitMQ without changing domain or handlers.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from src.shared.domain.domain_event import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: EventHandler,
    ) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._subscribers.get(type(event), [])
        for handler in handlers:
            await handler(event)

    async def publish_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)

    def subscriber_count(self, event_type: type[DomainEvent]) -> int:
        return len(self._subscribers.get(event_type, []))

    def clear(self) -> None:
        self._subscribers.clear()
