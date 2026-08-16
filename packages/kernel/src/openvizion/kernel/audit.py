"""Audit port — products record security-relevant actions without PII dumps."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditRecord:
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    action: str
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    resource_type: str | None = None
    resource_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditProvider(Protocol):
    async def record(self, entry: AuditRecord) -> None: ...
