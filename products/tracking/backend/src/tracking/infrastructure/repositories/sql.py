from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tracking.domain.entities.device import Device
from tracking.domain.entities.geofence import Geofence
from tracking.domain.entities.position import Position
from tracking.domain.entities.vehicle import Vehicle
from tracking.domain.value_objects.geo import GeoPoint, Polygon
from tracking.infrastructure.database.models import (
    DeviceModel,
    GeofenceModel,
    PositionModel,
    VehicleModel,
)


class SqlDeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, tenant_id: UUID, device_id: UUID) -> Device | None:
        row = await self._session.get(DeviceModel, device_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return _to_device(row)

    async def get_by_imei(self, tenant_id: UUID, imei: str) -> Device | None:
        result = await self._session.execute(
            select(DeviceModel).where(DeviceModel.tenant_id == tenant_id, DeviceModel.imei == imei)
        )
        row = result.scalar_one_or_none()
        return _to_device(row) if row else None

    async def list(self, tenant_id: UUID) -> list[Device]:
        result = await self._session.execute(
            select(DeviceModel).where(DeviceModel.tenant_id == tenant_id).order_by(DeviceModel.name)
        )
        return [_to_device(row) for row in result.scalars().all()]

    async def save(self, device: Device) -> None:
        row = await self._session.get(DeviceModel, device.id)
        if row is None:
            self._session.add(
                DeviceModel(
                    id=device.id,
                    tenant_id=device.tenant_id,
                    imei=device.imei,
                    name=device.name,
                    vehicle_id=device.vehicle_id,
                    is_active=device.is_active,
                    created_at=device.created_at,
                )
            )
            return
        if row.tenant_id != device.tenant_id:
            return
        row.name = device.name
        row.vehicle_id = device.vehicle_id
        row.is_active = device.is_active

    async def delete(self, tenant_id: UUID, device_id: UUID) -> None:
        row = await self._session.get(DeviceModel, device_id)
        if row is not None and row.tenant_id == tenant_id:
            await self._session.delete(row)


class SqlVehicleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, tenant_id: UUID, vehicle_id: UUID) -> Vehicle | None:
        row = await self._session.get(VehicleModel, vehicle_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return _to_vehicle(row)

    async def list(self, tenant_id: UUID) -> list[Vehicle]:
        result = await self._session.execute(
            select(VehicleModel).where(VehicleModel.tenant_id == tenant_id)
        )
        return [_to_vehicle(row) for row in result.scalars().all()]

    async def save(self, vehicle: Vehicle) -> None:
        existing = await self._session.get(VehicleModel, vehicle.id)
        if existing is None:
            self._session.add(
                VehicleModel(
                    id=vehicle.id,
                    tenant_id=vehicle.tenant_id,
                    plate=vehicle.plate,
                    name=vehicle.name,
                    device_id=vehicle.device_id,
                    is_active=vehicle.is_active,
                    created_at=vehicle.created_at,
                )
            )
            return
        if existing.tenant_id != vehicle.tenant_id:
            return
        existing.name = vehicle.name
        existing.device_id = vehicle.device_id
        existing.is_active = vehicle.is_active

    async def delete(self, tenant_id: UUID, vehicle_id: UUID) -> None:
        row = await self._session.get(VehicleModel, vehicle_id)
        if row is not None and row.tenant_id == tenant_id:
            await self._session.delete(row)


class SqlPositionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_event_id(self, tenant_id: UUID, event_id: UUID) -> Position | None:
        result = await self._session.execute(
            select(PositionModel).where(
                PositionModel.tenant_id == tenant_id, PositionModel.event_id == event_id
            )
        )
        row = result.scalar_one_or_none()
        return _to_position(row) if row else None

    async def latest_for_device(self, tenant_id: UUID, device_id: UUID) -> Position | None:
        result = await self._session.execute(
            select(PositionModel)
            .where(PositionModel.tenant_id == tenant_id, PositionModel.device_id == device_id)
            .order_by(PositionModel.recorded_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _to_position(row) if row else None

    async def list_recent(self, tenant_id: UUID, *, limit: int = 100) -> list[Position]:
        result = await self._session.execute(
            select(PositionModel)
            .where(PositionModel.tenant_id == tenant_id)
            .order_by(PositionModel.recorded_at.desc())
            .limit(limit)
        )
        return [_to_position(row) for row in result.scalars().all()]

    async def save(self, position: Position) -> None:
        self._session.add(
            PositionModel(
                id=position.id,
                tenant_id=position.tenant_id,
                device_id=position.device_id,
                event_id=position.event_id,
                latitude=position.latitude,
                longitude=position.longitude,
                speed_kmh=position.speed_kmh,
                heading=position.heading,
                recorded_at=position.recorded_at,
                processed=position.processed,
            )
        )

    async def list_unprocessed(self, tenant_id: UUID | None, *, limit: int = 50) -> list[Position]:
        stmt = select(PositionModel).where(PositionModel.processed.is_(False)).limit(limit)
        if tenant_id is not None:
            stmt = stmt.where(PositionModel.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return [_to_position(row) for row in result.scalars().all()]

    async def mark_processed(self, position_id: UUID) -> None:
        row = await self._session.get(PositionModel, position_id)
        if row is not None:
            row.processed = True


class SqlGeofenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, tenant_id: UUID, geofence_id: UUID) -> Geofence | None:
        row = await self._session.get(GeofenceModel, geofence_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return _to_geofence(row)

    async def list(self, tenant_id: UUID) -> list[Geofence]:
        result = await self._session.execute(
            select(GeofenceModel).where(GeofenceModel.tenant_id == tenant_id)
        )
        return [_to_geofence(row) for row in result.scalars().all()]

    async def save(self, geofence: Geofence) -> None:
        existing = await self._session.get(GeofenceModel, geofence.id)
        vertices = [[p.latitude, p.longitude] for p in geofence.polygon.vertices]
        if existing is None:
            self._session.add(
                GeofenceModel(
                    id=geofence.id,
                    tenant_id=geofence.tenant_id,
                    name=geofence.name,
                    vertices=vertices,
                    is_active=geofence.is_active,
                )
            )
            return
        if existing.tenant_id != geofence.tenant_id:
            return
        existing.name = geofence.name
        existing.vertices = vertices
        existing.is_active = geofence.is_active

    async def delete(self, tenant_id: UUID, geofence_id: UUID) -> None:
        row = await self._session.get(GeofenceModel, geofence_id)
        if row is not None and row.tenant_id == tenant_id:
            await self._session.delete(row)


def _to_device(row: DeviceModel) -> Device:
    return Device(
        id=row.id,
        tenant_id=row.tenant_id,
        imei=row.imei,
        name=row.name,
        vehicle_id=row.vehicle_id,
        is_active=row.is_active,
        created_at=row.created_at,
    )


def _to_vehicle(row: VehicleModel) -> Vehicle:
    return Vehicle(
        id=row.id,
        tenant_id=row.tenant_id,
        plate=row.plate,
        name=row.name,
        device_id=row.device_id,
        is_active=row.is_active,
        created_at=row.created_at,
    )


def _to_position(row: PositionModel) -> Position:
    return Position(
        id=row.id,
        tenant_id=row.tenant_id,
        device_id=row.device_id,
        event_id=row.event_id,
        latitude=row.latitude,
        longitude=row.longitude,
        speed_kmh=row.speed_kmh,
        heading=row.heading,
        recorded_at=row.recorded_at,
        processed=row.processed,
    )


def _to_geofence(row: GeofenceModel) -> Geofence:
    vertices = tuple(GeoPoint(latitude=float(lat), longitude=float(lng)) for lat, lng in row.vertices)
    return Geofence(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        polygon=Polygon(vertices=vertices),
        is_active=row.is_active,
    )
