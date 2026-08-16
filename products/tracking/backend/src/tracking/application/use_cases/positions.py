from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from openvizion.contracts.events import EventEnvelope
from openvizion.events.adapter import EventBusAdapter
from openvizion.kernel.entitlements import EntitlementProvider

from tracking.application.ports.repositories import DeviceRepository, PositionRepository
from tracking.domain.entities.position import Position
from tracking.domain.errors import NotFoundError, ValidationError
from tracking.permissions import CAPABILITY_ADVANCED_TELEMETRY


@dataclass(frozen=True, slots=True)
class IngestPositionCommand:
    tenant_id: UUID
    device_id: UUID
    latitude: float
    longitude: float
    event_id: UUID
    speed_kmh: float | None = None
    heading: float | None = None
    recorded_at: datetime | None = None


class IngestPositionUseCase:
    def __init__(
        self,
        *,
        devices: DeviceRepository,
        positions: PositionRepository,
        events: EventBusAdapter,
        entitlements: EntitlementProvider,
        producer: str = "tracking",
    ) -> None:
        self._devices = devices
        self._positions = positions
        self._events = events
        self._entitlements = entitlements
        self._producer = producer

    async def execute(self, command: IngestPositionCommand) -> tuple[Position, bool]:
        device = await self._devices.get(command.tenant_id, command.device_id)
        if device is None:
            raise NotFoundError("Device not found")
        existing = await self._positions.get_by_event_id(command.tenant_id, command.event_id)
        if existing is not None:
            return existing, False
        if not -90 <= command.latitude <= 90 or not -180 <= command.longitude <= 180:
            raise ValidationError("invalid coordinates")
        advanced = await self._entitlements.has(command.tenant_id, CAPABILITY_ADVANCED_TELEMETRY)
        speed = command.speed_kmh if advanced else None
        heading = command.heading if advanced else None
        position = Position(
            id=uuid4(),
            tenant_id=command.tenant_id,
            device_id=command.device_id,
            latitude=command.latitude,
            longitude=command.longitude,
            event_id=command.event_id,
            speed_kmh=speed,
            heading=heading,
            recorded_at=command.recorded_at or datetime.now(UTC),
        )
        await self._positions.save(position)
        await self._events.publish(
            EventEnvelope(
                event_type="tracking.PositionReceived",
                tenant_id=command.tenant_id,
                producer=self._producer,
                payload={
                    "device_id": str(command.device_id),
                    "event_id": str(command.event_id),
                    "latitude": command.latitude,
                    "longitude": command.longitude,
                },
            )
        )
        return position, True


class ListPositionsUseCase:
    def __init__(self, positions: PositionRepository) -> None:
        self._positions = positions

    async def execute(self, tenant_id: UUID, *, limit: int = 100) -> list[Position]:
        return await self._positions.list_recent(tenant_id, limit=limit)
