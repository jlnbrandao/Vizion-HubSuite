"""Usage metering — record and read what each tenant consumed per service.

`record()` is an upsert on (tenant, service, metric, granularity, period), so a
metered call costs one statement and the table holds one row per period instead of
one row per request.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.modules.services.usage_models import (
    GRANULARITIES,
    GRANULARITY_DAY,
    GRANULARITY_MONTH,
    UsageRecordModel,
)
from src.shared.infrastructure.exceptions import ValidationError
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import bind_rls_bypass, unbind_rls_bypass


@dataclass(frozen=True, slots=True)
class UsageRow:
    service: str
    metric: str
    granularity: str
    period_start: datetime
    quantity: int


def period_start_for(moment: datetime, granularity: str) -> datetime:
    """Truncate an instant to the start of its billing period (UTC)."""
    moment = moment.astimezone(UTC)
    if granularity == GRANULARITY_MONTH:
        return moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


class UsageService:
    async def record(
        self,
        *,
        tenant_id: UUID,
        service: str,
        metric: str,
        quantity: int = 1,
        granularity: str = GRANULARITY_DAY,
        moment: datetime | None = None,
    ) -> None:
        if granularity not in GRANULARITIES:
            raise ValidationError(f"granularity must be one of: {', '.join(sorted(GRANULARITIES))}")
        if quantity < 0:
            raise ValidationError("quantity must not be negative")

        period_start = period_start_for(moment or datetime.now(UTC), granularity)
        stmt = (
            pg_insert(UsageRecordModel)
            .values(
                id=uuid4(),
                tenant_id=tenant_id,
                service=service,
                metric=metric,
                granularity=granularity,
                period_start=period_start,
                quantity=quantity,
            )
            .on_conflict_do_update(
                constraint="uq_usage_records_period",
                set_={
                    "quantity": UsageRecordModel.quantity + quantity,
                    "updated_at": func.now(),
                },
            )
        )
        await get_current_session().execute(stmt)

    async def list_usage(
        self,
        *,
        tenant_id: UUID,
        since: datetime | None = None,
        until: datetime | None = None,
        service: str | None = None,
        granularity: str | None = None,
    ) -> list[UsageRow]:
        stmt = (
            select(UsageRecordModel)
            .where(UsageRecordModel.tenant_id == tenant_id)
            .order_by(
                UsageRecordModel.period_start.desc(),
                UsageRecordModel.service,
                UsageRecordModel.metric,
            )
        )
        if since is not None:
            stmt = stmt.where(UsageRecordModel.period_start >= since)
        if until is not None:
            stmt = stmt.where(UsageRecordModel.period_start <= until)
        if service:
            stmt = stmt.where(UsageRecordModel.service == service)
        if granularity:
            stmt = stmt.where(UsageRecordModel.granularity == granularity)

        result = await get_current_session().execute(stmt)
        return [
            UsageRow(
                service=row.service,
                metric=row.metric,
                granularity=row.granularity,
                period_start=row.period_start,
                quantity=row.quantity,
            )
            for row in result.scalars().all()
        ]

    async def totals_by_service(
        self,
        *,
        tenant_id: UUID,
        since: datetime | None = None,
    ) -> dict[str, int]:
        stmt = (
            select(UsageRecordModel.service, func.sum(UsageRecordModel.quantity))
            .where(UsageRecordModel.tenant_id == tenant_id)
            .group_by(UsageRecordModel.service)
        )
        if since is not None:
            stmt = stmt.where(UsageRecordModel.period_start >= since)
        result = await get_current_session().execute(stmt)
        return {service: int(total or 0) for service, total in result.all()}


class PlatformUsageService:
    """Cross-tenant reads for PLATFORM administration (RLS bypass on purpose)."""

    def __init__(self, usage: UsageService) -> None:
        self._usage = usage

    async def list_usage(self, **kwargs: Any) -> list[UsageRow]:
        token = bind_rls_bypass(True)
        try:
            return await self._usage.list_usage(**kwargs)
        finally:
            unbind_rls_bypass(token)

    async def totals_by_service(self, **kwargs: Any) -> dict[str, int]:
        token = bind_rls_bypass(True)
        try:
            return await self._usage.totals_by_service(**kwargs)
        finally:
            unbind_rls_bypass(token)
