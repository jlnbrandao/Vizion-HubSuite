"""Kafka EventBusAdapter. Optional: standalone never imports this at runtime unless selected."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Protocol

from openvizion.contracts.events import EventEnvelope
from openvizion.events.adapter import EventHandler


class KafkaProducer(Protocol):
    async def send_and_wait(self, topic: str, value: bytes, key: bytes | None = None) -> Any: ...

    async def stop(self) -> None: ...


class KafkaEventBus:
    """Publishes JSON envelopes to `{prefix}.{event_type}`.

    The producer is injected so unit tests do not need a broker. Production
    wiring may pass an aiokafka AIOKafkaProducer.
    """

    def __init__(
        self,
        *,
        producer: KafkaProducer,
        topic_prefix: str = "openvizion",
    ) -> None:
        self._producer = producer
        self._prefix = topic_prefix.strip(".") or "openvizion"
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self.published: list[EventEnvelope] = []

    def topic_for(self, event_type: str) -> str:
        safe = event_type.replace(".", "-")
        return f"{self._prefix}.{safe}"

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, envelope: EventEnvelope) -> None:
        self.published.append(envelope)
        payload = json.dumps(envelope.to_dict(), default=str).encode("utf-8")
        key = str(envelope.tenant_id).encode("utf-8")
        await self._producer.send_and_wait(self.topic_for(envelope.event_type), payload, key=key)
        for handler in list(self._subscribers.get(envelope.event_type, [])):
            await handler(envelope)

    async def aclose(self) -> None:
        await self._producer.stop()
