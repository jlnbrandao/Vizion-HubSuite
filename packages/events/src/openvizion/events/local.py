"""In-process event bus. Standalone products never need Kafka."""

from __future__ import annotations

from collections import defaultdict

from openvizion.contracts.events import EventEnvelope
from openvizion.events.adapter import EventHandler


class LocalEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self.published: list[EventEnvelope] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, envelope: EventEnvelope) -> None:
        self.published.append(envelope)
        for handler in list(self._subscribers.get(envelope.event_type, [])):
            await handler(envelope)
        for handler in list(self._subscribers.get("*", [])):
            await handler(envelope)

    def subscriber_count(self, event_type: str) -> int:
        return len(self._subscribers.get(event_type, []))

    def clear(self) -> None:
        self._subscribers.clear()
        self.published.clear()
