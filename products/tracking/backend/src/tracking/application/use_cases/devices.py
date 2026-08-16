from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from tracking.application.ports.repositories import DeviceRepository
from tracking.domain.entities.device import Device
from tracking.domain.errors import ConflictError, NotFoundError, ValidationError


@dataclass(frozen=True, slots=True)
class CreateDeviceCommand:
    tenant_id: UUID
    imei: str
    name: str
    vehicle_id: UUID | None = None


class CreateDeviceUseCase:
    def __init__(self, devices: DeviceRepository) -> None:
        self._devices = devices

    async def execute(self, command: CreateDeviceCommand) -> Device:
        imei = command.imei.strip()
        name = command.name.strip()
        if not imei or not name:
            raise ValidationError("imei and name are required")
        existing = await self._devices.get_by_imei(command.tenant_id, imei)
        if existing is not None:
            raise ConflictError(f"Device already exists: {imei}")
        device = Device(
            id=uuid4(),
            tenant_id=command.tenant_id,
            imei=imei,
            name=name,
            vehicle_id=command.vehicle_id,
        )
        await self._devices.save(device)
        return device


class ListDevicesUseCase:
    def __init__(self, devices: DeviceRepository) -> None:
        self._devices = devices

    async def execute(self, tenant_id: UUID) -> list[Device]:
        return await self._devices.list(tenant_id)


class GetDeviceUseCase:
    def __init__(self, devices: DeviceRepository) -> None:
        self._devices = devices

    async def execute(self, tenant_id: UUID, device_id: UUID) -> Device:
        device = await self._devices.get(tenant_id, device_id)
        if device is None:
            raise NotFoundError("Device not found")
        return device


class DeleteDeviceUseCase:
    def __init__(self, devices: DeviceRepository) -> None:
        self._devices = devices

    async def execute(self, tenant_id: UUID, device_id: UUID) -> None:
        device = await self._devices.get(tenant_id, device_id)
        if device is None:
            raise NotFoundError("Device not found")
        await self._devices.delete(tenant_id, device_id)
