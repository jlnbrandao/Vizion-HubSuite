"""Provider contract for outbound integration protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class IntegrationTestResult:
    success: bool
    message: str
    server: str | None = None
    duration_ms: int | None = None
    authentication: str | None = None
    permission: str | None = None
    error_detail: str | None = None


@dataclass(frozen=True, slots=True)
class IntegrationSyncResult:
    success: bool
    mode: str  # full | incremental
    records_processed: int
    message: str
    started_at: str
    finished_at: str
    # When set, IntegrationService persists into configuration.cursor_value.
    cursor_value: str | None = None


class IntegrationProvider(Protocol):
    type: str

    async def test_connection(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationTestResult: ...

    async def sync(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationSyncResult: ...
