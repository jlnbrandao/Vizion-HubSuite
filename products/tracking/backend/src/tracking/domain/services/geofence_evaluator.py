from __future__ import annotations

from tracking.domain.entities.geofence import Geofence
from tracking.domain.entities.position import Position
from tracking.domain.events.tracking_events import GeofenceTransition
from tracking.domain.value_objects.geo import GeoPoint


class GeofenceEvaluator:
    def evaluate(
        self,
        *,
        position: Position,
        fences: list[Geofence],
        previously_inside: set[str],
    ) -> list[GeofenceTransition]:
        point = GeoPoint(latitude=position.latitude, longitude=position.longitude)
        transitions: list[GeofenceTransition] = []
        for fence in fences:
            if not fence.is_active:
                continue
            inside = fence.contains(point)
            key = str(fence.id)
            was_inside = key in previously_inside
            if inside and not was_inside:
                transitions.append(
                    GeofenceTransition(
                        geofence_id=fence.id,
                        device_id=position.device_id,
                        kind="entered",
                        point=point,
                    )
                )
            elif not inside and was_inside:
                transitions.append(
                    GeofenceTransition(
                        geofence_id=fence.id,
                        device_id=position.device_id,
                        kind="exited",
                        point=point,
                    )
                )
        return transitions
