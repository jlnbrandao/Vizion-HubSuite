from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from tracking.domain.value_objects.geo import GeoPoint, Polygon


@dataclass
class Geofence:
    tenant_id: UUID
    name: str
    polygon: Polygon
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True

    def contains(self, point: GeoPoint) -> bool:
        return self.polygon.contains(point)
