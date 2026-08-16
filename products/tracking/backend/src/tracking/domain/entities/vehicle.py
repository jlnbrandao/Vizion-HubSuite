from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class Vehicle:
    tenant_id: UUID
    plate: str
    name: str
    id: UUID = field(default_factory=uuid4)
    device_id: UUID | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
