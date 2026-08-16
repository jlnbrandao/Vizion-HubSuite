"""EventBusAdapter — domain publishes events; infrastructure chooses the transport."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from openvizion.contracts.events import EventEnvelope

EventHandler = Callable[[EventEnvelope], Awaitable[None]]


class EventBusAdapter(Protocol):
    async def publish(self, envelope: EventEnvelope) -> None: ...

    def subscribe(self, event_type: str, handler: EventHandler) -> None: ...
