from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from openvizion.kernel.identity import Principal

from tracking.application.use_cases.devices import (
    CreateDeviceCommand,
    CreateDeviceUseCase,
    DeleteDeviceUseCase,
    ListDevicesUseCase,
)
from tracking.application.use_cases.geofences import (
    CreateGeofenceCommand,
    CreateGeofenceUseCase,
    DeleteGeofenceUseCase,
    ListGeofencesUseCase,
)
from tracking.application.use_cases.positions import (
    IngestPositionCommand,
    IngestPositionUseCase,
    ListPositionsUseCase,
)
from tracking.application.use_cases.vehicles import (
    CreateVehicleCommand,
    CreateVehicleUseCase,
    DeleteVehicleUseCase,
    ListVehiclesUseCase,
)
from tracking.infrastructure.composition import AppContainer
from tracking.infrastructure.repositories.sql import (
    SqlDeviceRepository,
    SqlGeofenceRepository,
    SqlPositionRepository,
    SqlVehicleRepository,
)
from tracking.interfaces.api.deps import (
    devices_repo,
    geofences_repo,
    get_container,
    positions_repo,
    require_permission,
    vehicles_repo,
)
from tracking.permissions import (
    DEVICES_CREATE,
    DEVICES_DELETE,
    DEVICES_READ,
    GEOFENCES_CREATE,
    GEOFENCES_DELETE,
    GEOFENCES_READ,
    POSITIONS_INGEST,
    POSITIONS_READ,
    VEHICLES_CREATE,
    VEHICLES_DELETE,
    VEHICLES_READ,
)

router = APIRouter(tags=["tracking"])


class DeviceBody(BaseModel):
    imei: str
    name: str
    vehicle_id: UUID | None = None


class DeviceOut(BaseModel):
    id: UUID
    imei: str
    name: str
    vehicle_id: UUID | None
    is_active: bool


class VehicleBody(BaseModel):
    plate: str
    name: str
    device_id: UUID | None = None


class VehicleOut(BaseModel):
    id: UUID
    plate: str
    name: str
    device_id: UUID | None
    is_active: bool


class PositionBody(BaseModel):
    device_id: UUID
    latitude: float
    longitude: float
    event_id: UUID | None = None
    speed_kmh: float | None = None
    heading: float | None = None
    recorded_at: datetime | None = None


class PositionOut(BaseModel):
    id: UUID
    device_id: UUID
    event_id: UUID
    latitude: float
    longitude: float
    speed_kmh: float | None
    heading: float | None
    recorded_at: datetime
    created: bool = True


class GeofenceBody(BaseModel):
    name: str
    vertices: list[tuple[float, float]] = Field(min_length=3)


class GeofenceOut(BaseModel):
    id: UUID
    name: str
    vertices: list[tuple[float, float]]
    is_active: bool


@router.get("/devices", response_model=list[DeviceOut])
async def list_devices(
    principal: Principal = Depends(require_permission(DEVICES_READ)),
    repo: SqlDeviceRepository = Depends(devices_repo),
) -> list[DeviceOut]:
    items = await ListDevicesUseCase(repo).execute(principal.tenant_id)
    return [DeviceOut.model_validate(item, from_attributes=True) for item in items]


@router.post("/devices", response_model=DeviceOut)
async def create_device(
    body: DeviceBody,
    principal: Principal = Depends(require_permission(DEVICES_CREATE)),
    repo: SqlDeviceRepository = Depends(devices_repo),
) -> DeviceOut:
    item = await CreateDeviceUseCase(repo).execute(
        CreateDeviceCommand(
            tenant_id=principal.tenant_id,
            imei=body.imei,
            name=body.name,
            vehicle_id=body.vehicle_id,
        )
    )
    return DeviceOut.model_validate(item, from_attributes=True)


@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: UUID,
    principal: Principal = Depends(require_permission(DEVICES_DELETE)),
    repo: SqlDeviceRepository = Depends(devices_repo),
) -> dict[str, str]:
    await DeleteDeviceUseCase(repo).execute(principal.tenant_id, device_id)
    return {"status": "ok"}


@router.get("/vehicles", response_model=list[VehicleOut])
async def list_vehicles(
    principal: Principal = Depends(require_permission(VEHICLES_READ)),
    repo: SqlVehicleRepository = Depends(vehicles_repo),
) -> list[VehicleOut]:
    items = await ListVehiclesUseCase(repo).execute(principal.tenant_id)
    return [VehicleOut.model_validate(item, from_attributes=True) for item in items]


@router.post("/vehicles", response_model=VehicleOut)
async def create_vehicle(
    body: VehicleBody,
    principal: Principal = Depends(require_permission(VEHICLES_CREATE)),
    repo: SqlVehicleRepository = Depends(vehicles_repo),
) -> VehicleOut:
    item = await CreateVehicleUseCase(repo).execute(
        CreateVehicleCommand(
            tenant_id=principal.tenant_id,
            plate=body.plate,
            name=body.name,
            device_id=body.device_id,
        )
    )
    return VehicleOut.model_validate(item, from_attributes=True)


@router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: UUID,
    principal: Principal = Depends(require_permission(VEHICLES_DELETE)),
    repo: SqlVehicleRepository = Depends(vehicles_repo),
) -> dict[str, str]:
    await DeleteVehicleUseCase(repo).execute(principal.tenant_id, vehicle_id)
    return {"status": "ok"}


@router.get("/positions", response_model=list[PositionOut])
async def list_positions(
    principal: Principal = Depends(require_permission(POSITIONS_READ)),
    repo: SqlPositionRepository = Depends(positions_repo),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PositionOut]:
    items = await ListPositionsUseCase(repo).execute(principal.tenant_id, limit=limit)
    return [
        PositionOut.model_validate(item, from_attributes=True).model_copy(update={"created": True})
        for item in items
    ]


@router.post("/positions", response_model=PositionOut)
async def ingest_position(
    body: PositionBody,
    principal: Principal = Depends(require_permission(POSITIONS_INGEST)),
    devices: SqlDeviceRepository = Depends(devices_repo),
    positions: SqlPositionRepository = Depends(positions_repo),
    container: AppContainer = Depends(get_container),
) -> PositionOut:
    item, created = await IngestPositionUseCase(
        devices=devices,
        positions=positions,
        events=container.event_bus,
        entitlements=container.entitlements,
        producer=container.settings.service_name,
    ).execute(
        IngestPositionCommand(
            tenant_id=principal.tenant_id,
            device_id=body.device_id,
            latitude=body.latitude,
            longitude=body.longitude,
            event_id=body.event_id or uuid4(),
            speed_kmh=body.speed_kmh,
            heading=body.heading,
            recorded_at=body.recorded_at,
        )
    )
    out = PositionOut.model_validate(item, from_attributes=True)
    return out.model_copy(update={"created": created})


@router.get("/geofences", response_model=list[GeofenceOut])
async def list_geofences(
    principal: Principal = Depends(require_permission(GEOFENCES_READ)),
    repo: SqlGeofenceRepository = Depends(geofences_repo),
) -> list[GeofenceOut]:
    items = await ListGeofencesUseCase(repo).execute(principal.tenant_id)
    return [
        GeofenceOut(
            id=item.id,
            name=item.name,
            vertices=[(p.latitude, p.longitude) for p in item.polygon.vertices],
            is_active=item.is_active,
        )
        for item in items
    ]


@router.post("/geofences", response_model=GeofenceOut)
async def create_geofence(
    body: GeofenceBody,
    principal: Principal = Depends(require_permission(GEOFENCES_CREATE)),
    repo: SqlGeofenceRepository = Depends(geofences_repo),
) -> GeofenceOut:
    item = await CreateGeofenceUseCase(repo).execute(
        CreateGeofenceCommand(
            tenant_id=principal.tenant_id,
            name=body.name,
            vertices=tuple(body.vertices),
        )
    )
    return GeofenceOut(
        id=item.id,
        name=item.name,
        vertices=[(p.latitude, p.longitude) for p in item.polygon.vertices],
        is_active=item.is_active,
    )


@router.delete("/geofences/{geofence_id}")
async def delete_geofence(
    geofence_id: UUID,
    principal: Principal = Depends(require_permission(GEOFENCES_DELETE)),
    repo: SqlGeofenceRepository = Depends(geofences_repo),
) -> dict[str, str]:
    await DeleteGeofenceUseCase(repo).execute(principal.tenant_id, geofence_id)
    return {"status": "ok"}
