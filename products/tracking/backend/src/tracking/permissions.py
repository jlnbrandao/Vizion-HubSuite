"""Tracking permission and entitlement catalogs."""

from __future__ import annotations

SERVICE = "tracking"

DEVICES_READ = "tracking.devices.read"
DEVICES_CREATE = "tracking.devices.create"
DEVICES_UPDATE = "tracking.devices.update"
DEVICES_DELETE = "tracking.devices.delete"
VEHICLES_READ = "tracking.vehicles.read"
VEHICLES_CREATE = "tracking.vehicles.create"
VEHICLES_UPDATE = "tracking.vehicles.update"
VEHICLES_DELETE = "tracking.vehicles.delete"
POSITIONS_READ = "tracking.positions.read"
POSITIONS_INGEST = "tracking.positions.ingest"
GEOFENCES_READ = "tracking.geofences.read"
GEOFENCES_CREATE = "tracking.geofences.create"
GEOFENCES_UPDATE = "tracking.geofences.update"
GEOFENCES_DELETE = "tracking.geofences.delete"
USERS_MANAGE = "tracking.users.manage"

ALL_PERMISSIONS: frozenset[str] = frozenset(
    {
        DEVICES_READ,
        DEVICES_CREATE,
        DEVICES_UPDATE,
        DEVICES_DELETE,
        VEHICLES_READ,
        VEHICLES_CREATE,
        VEHICLES_UPDATE,
        VEHICLES_DELETE,
        POSITIONS_READ,
        POSITIONS_INGEST,
        GEOFENCES_READ,
        GEOFENCES_CREATE,
        GEOFENCES_UPDATE,
        GEOFENCES_DELETE,
        USERS_MANAGE,
    }
)

ADMIN_PERMISSIONS = ALL_PERMISSIONS
OPERATOR_PERMISSIONS = frozenset(
    {
        DEVICES_READ,
        DEVICES_CREATE,
        DEVICES_UPDATE,
        VEHICLES_READ,
        POSITIONS_READ,
        POSITIONS_INGEST,
        GEOFENCES_READ,
        GEOFENCES_CREATE,
        GEOFENCES_UPDATE,
    }
)
VIEWER_PERMISSIONS = frozenset(
    {DEVICES_READ, VEHICLES_READ, POSITIONS_READ, GEOFENCES_READ}
)

CAPABILITY_BASIC = "BASIC_TRACKING"
CAPABILITY_ADVANCED_TELEMETRY = "ADVANCED_TELEMETRY"

DEFAULT_CAPABILITIES = frozenset({CAPABILITY_BASIC})
