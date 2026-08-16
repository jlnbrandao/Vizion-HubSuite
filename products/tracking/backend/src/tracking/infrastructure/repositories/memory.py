"""In-memory repositories for unit tests — no database required."""

from __future__ import annotations

from uuid import UUID

from tracking.domain.entities.device import Device
from tracking.domain.entities.geofence import Geofence
from tracking.domain.entities.position import Position
from tracking.domain.entities.vehicle import Vehicle


class InMemoryDeviceRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Device] = {}

    async def get(self, tenant_id: UUID, device_id: UUID) -> Device | None:
        item = self.items.get(device_id)
        return item if item and item.tenant_id == tenant_id else None

    async def get_by_imei(self, tenant_id: UUID, imei: str) -> Device | None:
        return next(
            (item for item in self.items.values() if item.tenant_id == tenant_id and item.imei == imei),
            None,
        )

    async def list(self, tenant_id: UUID) -> list[Device]:
        return [item for item in self.items.values() if item.tenant_id == tenant_id]

    async def save(self, device: Device) -> None:
        self.items[device.id] = device

    async def delete(self, tenant_id: UUID, device_id: UUID) -> None:
        item = self.items.get(device_id)
        if item and item.tenant_id == tenant_id:
            del self.items[device_id]


class InMemoryVehicleRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Vehicle] = {}

    async def get(self, tenant_id: UUID, vehicle_id: UUID) -> Vehicle | None:
        item = self.items.get(vehicle_id)
        return item if item and item.tenant_id == tenant_id else None

    async def list(self, tenant_id: UUID) -> list[Vehicle]:
        return [item for item in self.items.values() if item.tenant_id == tenant_id]

    async def save(self, vehicle: Vehicle) -> None:
        self.items[vehicle.id] = vehicle

    async def delete(self, tenant_id: UUID, vehicle_id: UUID) -> None:
        item = self.items.get(vehicle_id)
        if item and item.tenant_id == tenant_id:
            del self.items[vehicle_id]


class InMemoryPositionRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Position] = {}

    async def get_by_event_id(self, tenant_id: UUID, event_id: UUID) -> Position | None:
        return next(
            (
                item
                for item in self.items.values()
                if item.tenant_id == tenant_id and item.event_id == event_id
            ),
            None,
        )

    async def latest_for_device(self, tenant_id: UUID, device_id: UUID) -> Position | None:
        matches = [
            item
            for item in self.items.values()
            if item.tenant_id == tenant_id and item.device_id == device_id
        ]
        matches.sort(key=lambda item: item.recorded_at, reverse=True)
        return matches[0] if matches else None

    async def list_recent(self, tenant_id: UUID, *, limit: int = 100) -> list[Position]:
        matches = [item for item in self.items.values() if item.tenant_id == tenant_id]
        matches.sort(key=lambda item: item.recorded_at, reverse=True)
        return matches[:limit]

    async def save(self, position: Position) -> None:
        self.items[position.id] = position

    async def list_unprocessed(self, tenant_id: UUID | None, *, limit: int = 50) -> list[Position]:
        matches = [
            item
            for item in self.items.values()
            if not item.processed and (tenant_id is None or item.tenant_id == tenant_id)
        ]
        return matches[:limit]

    async def mark_processed(self, position_id: UUID) -> None:
        item = self.items.get(position_id)
        if item:
            item.processed = True


class InMemoryGeofenceRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Geofence] = {}

    async def get(self, tenant_id: UUID, geofence_id: UUID) -> Geofence | None:
        item = self.items.get(geofence_id)
        return item if item and item.tenant_id == tenant_id else None

    async def list(self, tenant_id: UUID) -> list[Geofence]:
        return [item for item in self.items.values() if item.tenant_id == tenant_id]

    async def save(self, geofence: Geofence) -> None:
        self.items[geofence.id] = geofence

    async def delete(self, tenant_id: UUID, geofence_id: UUID) -> None:
        item = self.items.get(geofence_id)
        if item and item.tenant_id == tenant_id:
            del self.items[geofence_id]
