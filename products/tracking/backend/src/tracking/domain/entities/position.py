from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class Position:
    tenant_id: UUID
    device_id: UUID
    latitude: float
    longitude: float
    event_id: UUID
    id: UUID = field(default_factory=uuid4)
    speed_kmh: float | None = None
    heading: float | None = None
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processed: bool = False
