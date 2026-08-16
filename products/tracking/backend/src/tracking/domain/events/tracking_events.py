from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from tracking.domain.value_objects.geo import GeoPoint


@dataclass(frozen=True, slots=True)
class GeofenceTransition:
    geofence_id: UUID
    device_id: UUID
    kind: str  # entered | exited
    point: GeoPoint
