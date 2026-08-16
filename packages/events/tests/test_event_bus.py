from uuid import uuid4

import pytest

from openvizion.contracts.events import EventEnvelope
from openvizion.events.factory import create_event_bus
from openvizion.events.kafka import KafkaEventBus
from openvizion.events.local import LocalEventBus
from openvizion.kernel.configuration import AdapterSelection


TENANT = uuid4()


@pytest.mark.asyncio
async def test_local_event_bus_publish_and_subscribe() -> None:
    bus = LocalEventBus()
    seen: list[str] = []

    async def handler(envelope: EventEnvelope) -> None:
        seen.append(envelope.event_type)

    bus.subscribe("tracking.PositionReceived", handler)
    envelope = EventEnvelope(
        event_type="tracking.PositionReceived",
        tenant_id=TENANT,
        payload={"device_id": str(uuid4())},
    )
    await bus.publish(envelope)
    assert seen == ["tracking.PositionReceived"]
    assert bus.published[0].event_id == envelope.event_id


@pytest.mark.asyncio
async def test_local_event_bus_idempotent_envelope_ids() -> None:
    bus = LocalEventBus()
    envelope = EventEnvelope(
        event_type="tracking.PositionReceived",
        tenant_id=TENANT,
        payload={"seq": 1},
    )
    await bus.publish(envelope)
    await bus.publish(envelope)
    assert [item.event_id for item in bus.published] == [envelope.event_id, envelope.event_id]


class _FakeProducer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, bytes]] = []

    async def send_and_wait(self, topic: str, value: bytes, key: bytes | None = None) -> None:
        self.messages.append((topic, value))

    async def stop(self) -> None:
        return None


@pytest.mark.asyncio
async def test_kafka_event_bus_uses_injected_producer() -> None:
    producer = _FakeProducer()
    bus = KafkaEventBus(producer=producer, topic_prefix="ov")
    envelope = EventEnvelope(
        event_type="tracking.GeofenceEntered",
        tenant_id=TENANT,
        payload={},
    )
    await bus.publish(envelope)
    assert producer.messages[0][0] == "ov.tracking-GeofenceEntered"
    assert b"GeofenceEntered" in producer.messages[0][1]
    await bus.aclose()


def test_factory_local_and_kafka() -> None:
    local = create_event_bus(AdapterSelection.LOCAL)
    assert isinstance(local, LocalEventBus)
    kafka = create_event_bus(AdapterSelection.KAFKA, kafka_producer=_FakeProducer())
    assert isinstance(kafka, KafkaEventBus)
    with pytest.raises(ValueError, match="Kafka producer"):
        create_event_bus(AdapterSelection.KAFKA)
