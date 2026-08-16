from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from openvizion.contracts.events import EventEnvelope
from openvizion.events.adapter import EventBusAdapter

from tracking.application.ports.repositories import GeofenceRepository, PositionRepository
from tracking.domain.services.geofence_evaluator import GeofenceEvaluator


class ProcessPositionsUseCase:
    """Worker use case: evaluate unprocessed positions against geofences."""

    def __init__(
        self,
        *,
        positions: PositionRepository,
        geofences: GeofenceRepository,
        events: EventBusAdapter,
        evaluator: GeofenceEvaluator | None = None,
        inside_state: dict[tuple[UUID, UUID], set[str]] | None = None,
    ) -> None:
        self._positions = positions
        self._geofences = geofences
        self._events = events
        self._evaluator = evaluator or GeofenceEvaluator()
        self._inside: dict[tuple[UUID, UUID], set[str]] = inside_state or defaultdict(set)

    async def execute(self, *, limit: int = 50) -> int:
        rows = await self._positions.list_unprocessed(None, limit=limit)
        processed = 0
        for position in rows:
            fences = await self._geofences.list(position.tenant_id)
            key = (position.tenant_id, position.device_id)
            previous = set(self._inside[key])
            transitions = self._evaluator.evaluate(
                position=position,
                fences=fences,
                previously_inside=previous,
            )
            current = set(previous)
            for item in transitions:
                fence_key = str(item.geofence_id)
                event_type = (
                    "tracking.GeofenceEntered" if item.kind == "entered" else "tracking.GeofenceExited"
                )
                if item.kind == "entered":
                    current.add(fence_key)
                else:
                    current.discard(fence_key)
                await self._events.publish(
                    EventEnvelope(
                        event_type=event_type,
                        tenant_id=position.tenant_id,
                        producer="tracking-worker",
                        payload={
                            "device_id": str(item.device_id),
                            "geofence_id": str(item.geofence_id),
                            "latitude": item.point.latitude,
                            "longitude": item.point.longitude,
                        },
                    )
                )
            self._inside[key] = current
            await self._positions.mark_processed(position.id)
            processed += 1
        return processed
