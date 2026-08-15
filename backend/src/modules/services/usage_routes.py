"""Usage (metering) HTTP routes.

`GET /usage` answers for the caller's own tenant; the platform variant takes a
tenant id and requires `usage.read_all`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.modules.services.usage import PlatformUsageService, UsageRow, UsageService
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import require_permission
from src.shared.infrastructure.security.permission_codes import PermissionCode

router = APIRouter(prefix="/usage", tags=["usage"])

_DEFAULT_WINDOW_DAYS = 30


class UsageRecordResponse(BaseModel):
    service: str
    metric: str
    granularity: str
    period_start: datetime
    quantity: int


class UsageReportResponse(BaseModel):
    tenant_id: UUID
    since: datetime
    until: datetime
    totals_by_service: dict[str, int] = Field(default_factory=dict)
    records: list[UsageRecordResponse] = Field(default_factory=list)


def _to_response(row: UsageRow) -> UsageRecordResponse:
    return UsageRecordResponse(
        service=row.service,
        metric=row.metric,
        granularity=row.granularity,
        period_start=row.period_start,
        quantity=row.quantity,
    )


def _window(since: datetime | None, until: datetime | None) -> tuple[datetime, datetime]:
    resolved_until = until or datetime.now(UTC)
    resolved_since = since or resolved_until - timedelta(days=_DEFAULT_WINDOW_DAYS)
    return resolved_since, resolved_until


@router.get("", response_model=UsageReportResponse)
@inject
async def my_usage(
    since: datetime | None = None,
    until: datetime | None = None,
    service: str | None = None,
    granularity: str | None = Query(default=None, pattern="^(day|month)$"),
    actor: CurrentUser = Depends(require_permission(PermissionCode.USAGE_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    usage: UsageService = Depends(Provide[Container.usage_service]),
) -> UsageReportResponse:
    """Metered consumption of the caller's own tenant."""
    resolved_since, resolved_until = _window(since, until)
    async with uow_factory:
        rows = await usage.list_usage(
            tenant_id=actor.tenant_id,
            since=resolved_since,
            until=resolved_until,
            service=service,
            granularity=granularity,
        )
        totals = await usage.totals_by_service(
            tenant_id=actor.tenant_id, since=resolved_since
        )
    return UsageReportResponse(
        tenant_id=actor.tenant_id,
        since=resolved_since,
        until=resolved_until,
        totals_by_service=totals,
        records=[_to_response(row) for row in rows],
    )


@router.get("/tenants/{tenant_id}", response_model=UsageReportResponse)
@inject
async def tenant_usage(
    tenant_id: UUID,
    since: datetime | None = None,
    until: datetime | None = None,
    service: str | None = None,
    granularity: str | None = Query(default=None, pattern="^(day|month)$"),
    _: CurrentUser = Depends(require_permission(PermissionCode.USAGE_READ_ALL)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    platform: PlatformUsageService = Depends(Provide[Container.platform_usage_service]),
) -> UsageReportResponse:
    """Metered consumption of any tenant (platform administration)."""
    resolved_since, resolved_until = _window(since, until)
    async with uow_factory:
        rows = await platform.list_usage(
            tenant_id=tenant_id,
            since=resolved_since,
            until=resolved_until,
            service=service,
            granularity=granularity,
        )
        totals = await platform.totals_by_service(
            tenant_id=tenant_id, since=resolved_since
        )
    return UsageReportResponse(
        tenant_id=tenant_id,
        since=resolved_since,
        until=resolved_until,
        totals_by_service=totals,
        records=[_to_response(row) for row in rows],
    )
