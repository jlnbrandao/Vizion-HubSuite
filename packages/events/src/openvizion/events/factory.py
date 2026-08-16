from __future__ import annotations

from openvizion.events.adapter import EventBusAdapter
from openvizion.events.kafka import KafkaEventBus, KafkaProducer
from openvizion.events.local import LocalEventBus
from openvizion.kernel.configuration import AdapterSelection


def create_event_bus(
    adapter: AdapterSelection,
    *,
    kafka_producer: KafkaProducer | None = None,
    topic_prefix: str = "openvizion",
) -> EventBusAdapter:
    if adapter == AdapterSelection.KAFKA:
        if kafka_producer is None:
            raise ValueError("EVENT_BUS_ADAPTER=kafka requires a Kafka producer")
        return KafkaEventBus(producer=kafka_producer, topic_prefix=topic_prefix)
    if adapter in {AdapterSelection.LOCAL, AdapterSelection.HUB}:
        return LocalEventBus()
    raise ValueError(f"Unsupported EVENT_BUS_ADAPTER: {adapter}")
