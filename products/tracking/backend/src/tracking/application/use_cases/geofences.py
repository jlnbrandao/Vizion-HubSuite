from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from tracking.application.ports.repositories import GeofenceRepository
from tracking.domain.entities.geofence import Geofence
from tracking.domain.errors import NotFoundError, ValidationError
from tracking.domain.value_objects.geo import GeoPoint, Polygon


@dataclass(frozen=True, slots=True)
class CreateGeofenceCommand:
    tenant_id: UUID
    name: str
    vertices: tuple[tuple[float, float], ...]


class CreateGeofenceUseCase:
    def __init__(self, geofences: GeofenceRepository) -> None:
        self._geofences = geofences

    async def execute(self, command: CreateGeofenceCommand) -> Geofence:
        name = command.name.strip()
        if not name:
            raise ValidationError("name is required")
        polygon = Polygon(
            vertices=tuple(GeoPoint(latitude=lat, longitude=lng) for lat, lng in command.vertices)
        )
        fence = Geofence(
            id=uuid4(),
            tenant_id=command.tenant_id,
            name=name,
            polygon=polygon,
        )
        await self._geofences.save(fence)
        return fence


class ListGeofencesUseCase:
    def __init__(self, geofences: GeofenceRepository) -> None:
        self._geofences = geofences

    async def execute(self, tenant_id: UUID) -> list[Geofence]:
        return await self._geofences.list(tenant_id)


class DeleteGeofenceUseCase:
    def __init__(self, geofences: GeofenceRepository) -> None:
        self._geofences = geofences

    async def execute(self, tenant_id: UUID, geofence_id: UUID) -> None:
        fence = await self._geofences.get(tenant_id, geofence_id)
        if fence is None:
            raise NotFoundError("Geofence not found")
        await self._geofences.delete(tenant_id, geofence_id)
