from uuid import uuid4

import pytest

from openvizion.events.local import LocalEventBus
from openvizion.kernel.local_providers import LocalEntitlementProvider
from tracking.application.use_cases.devices import CreateDeviceCommand, CreateDeviceUseCase
from tracking.application.use_cases.positions import IngestPositionCommand, IngestPositionUseCase
from tracking.application.use_cases.process_positions import ProcessPositionsUseCase
from tracking.domain.entities.geofence import Geofence
from tracking.domain.errors import ConflictError
from tracking.domain.services.geofence_evaluator import GeofenceEvaluator
from tracking.domain.value_objects.geo import GeoPoint, Polygon
from tracking.infrastructure.repositories.memory import (
    InMemoryDeviceRepository,
    InMemoryGeofenceRepository,
    InMemoryPositionRepository,
)
from tracking.permissions import CAPABILITY_ADVANCED_TELEMETRY, CAPABILITY_BASIC

TENANT_A = uuid4()
TENANT_B = uuid4()


@pytest.mark.asyncio
async def test_create_device_and_conflict() -> None:
    repo = InMemoryDeviceRepository()
    use_case = CreateDeviceUseCase(repo)
    device = await use_case.execute(
        CreateDeviceCommand(tenant_id=TENANT_A, imei="123", name="Truck")
    )
    assert device.tenant_id == TENANT_A
    with pytest.raises(ConflictError):
        await use_case.execute(CreateDeviceCommand(tenant_id=TENANT_A, imei="123", name="Other"))


@pytest.mark.asyncio
async def test_tenant_isolation_on_list() -> None:
    repo = InMemoryDeviceRepository()
    use_case = CreateDeviceUseCase(repo)
    await use_case.execute(CreateDeviceCommand(tenant_id=TENANT_A, imei="a", name="A"))
    await use_case.execute(CreateDeviceCommand(tenant_id=TENANT_B, imei="b", name="B"))
    a_items = await repo.list(TENANT_A)
    b_items = await repo.list(TENANT_B)
    assert [item.imei for item in a_items] == ["a"]
    assert [item.imei for item in b_items] == ["b"]


@pytest.mark.asyncio
async def test_position_ingest_idempotent_and_events() -> None:
    devices = InMemoryDeviceRepository()
    positions = InMemoryPositionRepository()
    bus = LocalEventBus()
    entitlements = LocalEntitlementProvider()
    entitlements.grant(TENANT_A, CAPABILITY_BASIC, CAPABILITY_ADVANCED_TELEMETRY)
    device = await CreateDeviceUseCase(devices).execute(
        CreateDeviceCommand(tenant_id=TENANT_A, imei="1", name="D")
    )
    ingest = IngestPositionUseCase(
        devices=devices, positions=positions, events=bus, entitlements=entitlements
    )
    event_id = uuid4()
    first, created = await ingest.execute(
        IngestPositionCommand(
            tenant_id=TENANT_A,
            device_id=device.id,
            latitude=-23.5,
            longitude=-46.6,
            event_id=event_id,
            speed_kmh=40,
        )
    )
    second, created_again = await ingest.execute(
        IngestPositionCommand(
            tenant_id=TENANT_A,
            device_id=device.id,
            latitude=-23.5,
            longitude=-46.6,
            event_id=event_id,
            speed_kmh=99,
        )
    )
    assert created is True
    assert created_again is False
    assert first.id == second.id
    assert first.speed_kmh == 40
    assert len(bus.published) == 1
    assert bus.published[0].event_type == "tracking.PositionReceived"


@pytest.mark.asyncio
async def test_advanced_telemetry_entitlement_strips_speed() -> None:
    devices = InMemoryDeviceRepository()
    positions = InMemoryPositionRepository()
    bus = LocalEventBus()
    entitlements = LocalEntitlementProvider()
    entitlements.grant(TENANT_A, CAPABILITY_BASIC)
    device = await CreateDeviceUseCase(devices).execute(
        CreateDeviceCommand(tenant_id=TENANT_A, imei="1", name="D")
    )
    position, _ = await IngestPositionUseCase(
        devices=devices, positions=positions, events=bus, entitlements=entitlements
    ).execute(
        IngestPositionCommand(
            tenant_id=TENANT_A,
            device_id=device.id,
            latitude=1,
            longitude=1,
            event_id=uuid4(),
            speed_kmh=80,
            heading=90,
        )
    )
    assert position.speed_kmh is None
    assert position.heading is None


def test_point_in_polygon() -> None:
    square = Polygon(
        vertices=(
            GeoPoint(0, 0),
            GeoPoint(0, 10),
            GeoPoint(10, 10),
            GeoPoint(10, 0),
        )
    )
    assert square.contains(GeoPoint(5, 5))
    assert not square.contains(GeoPoint(20, 20))


@pytest.mark.asyncio
async def test_geofence_worker_publishes_enter() -> None:
    devices = InMemoryDeviceRepository()
    positions = InMemoryPositionRepository()
    geofences = InMemoryGeofenceRepository()
    bus = LocalEventBus()
    entitlements = LocalEntitlementProvider()
    entitlements.grant(TENANT_A, CAPABILITY_BASIC, CAPABILITY_ADVANCED_TELEMETRY)
    device = await CreateDeviceUseCase(devices).execute(
        CreateDeviceCommand(tenant_id=TENANT_A, imei="1", name="D")
    )
    await geofences.save(
        Geofence(
            tenant_id=TENANT_A,
            name="yard",
            polygon=Polygon(
                vertices=(
                    GeoPoint(-24, -47),
                    GeoPoint(-24, -46),
                    GeoPoint(-23, -46),
                    GeoPoint(-23, -47),
                )
            ),
        )
    )
    await IngestPositionUseCase(
        devices=devices, positions=positions, events=bus, entitlements=entitlements
    ).execute(
        IngestPositionCommand(
            tenant_id=TENANT_A,
            device_id=device.id,
            latitude=-23.5,
            longitude=-46.5,
            event_id=uuid4(),
        )
    )
    processed = await ProcessPositionsUseCase(
        positions=positions,
        geofences=geofences,
        events=bus,
        evaluator=GeofenceEvaluator(),
    ).execute()
    assert processed == 1
    types = [item.event_type for item in bus.published]
    assert "tracking.GeofenceEntered" in types
