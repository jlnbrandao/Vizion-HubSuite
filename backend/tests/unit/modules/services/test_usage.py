"""Metering: period truncation, upsert accumulation and quota-driven recording."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.modules.services.quotas import REQUESTS_PER_MINUTE, ServiceQuotaGuard
from src.modules.services.usage import UsageService, period_start_for
from src.modules.services.usage_models import GRANULARITY_DAY, GRANULARITY_MONTH
from src.shared.infrastructure.exceptions import RateLimitExceededError, ValidationError


def test_period_start_truncates_to_the_day() -> None:
    moment = datetime(2026, 3, 17, 13, 45, 12, tzinfo=UTC)

    assert period_start_for(moment, GRANULARITY_DAY) == datetime(2026, 3, 17, tzinfo=UTC)


def test_period_start_truncates_to_the_month() -> None:
    moment = datetime(2026, 3, 17, 13, 45, 12, tzinfo=UTC)

    assert period_start_for(moment, GRANULARITY_MONTH) == datetime(2026, 3, 1, tzinfo=UTC)


@pytest.mark.asyncio
async def test_record_rejects_unknown_granularity() -> None:
    with pytest.raises(ValidationError):
        await UsageService().record(
            tenant_id=uuid4(), service="iam", metric="calls", granularity="week"
        )


@pytest.mark.asyncio
async def test_record_rejects_negative_quantity() -> None:
    with pytest.raises(ValidationError):
        await UsageService().record(
            tenant_id=uuid4(), service="iam", metric="calls", quantity=-1
        )


class _FakeCatalog:
    def __init__(self, limit: int | None) -> None:
        self._limit = limit

    async def quota(self, *, tenant_id: UUID, namespace: str, key: str) -> int | None:
        return self._limit


class _FakeLimiter:
    def __init__(self, allowed: bool) -> None:
        self._allowed = allowed
        self.calls = 0

    async def is_allowed(
        self, key: str, *, limit: int, window_seconds: int
    ) -> tuple[bool, int]:
        self.calls += 1
        return self._allowed, limit - 1


class _RecordedUsage:
    def __init__(self) -> None:
        self.records: list[tuple[UUID, str, str]] = []

    async def record(self, *, tenant_id: UUID, service: str, metric: str) -> None:
        self.records.append((tenant_id, service, metric))


class _FakeUow:
    def __init__(self) -> None:
        self.committed = False

    async def __aenter__(self) -> _FakeUow:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


def _guard(*, limit: int | None, allowed: bool = True) -> tuple[ServiceQuotaGuard, _RecordedUsage]:
    usage = _RecordedUsage()
    guard = ServiceQuotaGuard(
        catalog=_FakeCatalog(limit),  # type: ignore[arg-type]
        rate_limiter=_FakeLimiter(allowed),  # type: ignore[arg-type]
        uow_factory=_FakeUow,
        usage=usage,  # type: ignore[arg-type]
    )
    return guard, usage


@pytest.mark.asyncio
async def test_unlimited_quota_is_still_metered() -> None:
    """No ceiling does not mean no accounting."""
    guard, usage = _guard(limit=None)

    remaining = await guard.enforce(tenant_id=uuid4(), namespace="integration")

    assert remaining == -1
    assert usage.records and usage.records[0][2] == REQUESTS_PER_MINUTE


@pytest.mark.asyncio
async def test_allowed_call_consumes_quota_and_records_usage() -> None:
    tenant_id = uuid4()
    guard, usage = _guard(limit=10)

    remaining = await guard.enforce(
        tenant_id=tenant_id, namespace="integration", metric="sync_per_hour"
    )

    assert remaining == 9
    assert usage.records == [(tenant_id, "integration", "sync_per_hour")]


@pytest.mark.asyncio
async def test_exhausted_quota_raises_and_records_nothing() -> None:
    guard, usage = _guard(limit=1, allowed=False)

    with pytest.raises(RateLimitExceededError):
        await guard.enforce(tenant_id=uuid4(), namespace="integration")

    assert usage.records == []


@pytest.mark.asyncio
async def test_metering_can_be_skipped_for_non_billable_checks() -> None:
    guard, usage = _guard(limit=10)

    await guard.enforce(tenant_id=uuid4(), namespace="integration", meter=False)

    assert usage.records == []
