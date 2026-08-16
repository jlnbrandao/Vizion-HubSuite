from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from tracking.application.ports.repositories import VehicleRepository
from tracking.domain.entities.vehicle import Vehicle
from tracking.domain.errors import NotFoundError, ValidationError


@dataclass(frozen=True, slots=True)
class CreateVehicleCommand:
    tenant_id: UUID
    plate: str
    name: str
    device_id: UUID | None = None


class CreateVehicleUseCase:
    def __init__(self, vehicles: VehicleRepository) -> None:
        self._vehicles = vehicles

    async def execute(self, command: CreateVehicleCommand) -> Vehicle:
        plate = command.plate.strip().upper()
        name = command.name.strip()
        if not plate or not name:
            raise ValidationError("plate and name are required")
        vehicle = Vehicle(
            id=uuid4(),
            tenant_id=command.tenant_id,
            plate=plate,
            name=name,
            device_id=command.device_id,
        )
        await self._vehicles.save(vehicle)
        return vehicle


class ListVehiclesUseCase:
    def __init__(self, vehicles: VehicleRepository) -> None:
        self._vehicles = vehicles

    async def execute(self, tenant_id: UUID) -> list[Vehicle]:
        return await self._vehicles.list(tenant_id)


class DeleteVehicleUseCase:
    def __init__(self, vehicles: VehicleRepository) -> None:
        self._vehicles = vehicles

    async def execute(self, tenant_id: UUID, vehicle_id: UUID) -> None:
        vehicle = await self._vehicles.get(tenant_id, vehicle_id)
        if vehicle is None:
            raise NotFoundError("Vehicle not found")
        await self._vehicles.delete(tenant_id, vehicle_id)
