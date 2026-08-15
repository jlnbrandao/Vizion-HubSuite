"""Per-tenant service quotas on top of the shared Redis limiter."""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from src.modules.services.quotas import ServiceQuotaGuard
from src.shared.infrastructure.exceptions import RateLimitExceededError
from src.shared.infrastructure.security.rate_limiter import InMemoryRateLimiter

TENANT_ID = uuid4()


class _FakeCatalog:
    def __init__(self, quotas: dict[str, int]) -> None:
        self.quotas = quotas

    async def quota(self, *, tenant_id, namespace, key):  # noqa: ANN001, ANN201
        return self.quotas.get(key)


@asynccontextmanager
async def _uow_factory():
    yield None


def _guard(quotas: dict[str, int]) -> ServiceQuotaGuard:
    return ServiceQuotaGuard(
        _FakeCatalog(quotas),  # type: ignore[arg-type]
        InMemoryRateLimiter(),
        _uow_factory,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_metric_without_a_quota_is_unlimited() -> None:
    guard = _guard({})

    assert await guard.enforce(tenant_id=TENANT_ID, namespace="gps") == -1


@pytest.mark.asyncio
async def test_window_is_exhausted_after_the_limit() -> None:
    guard = _guard({"requests_per_minute": 2})

    assert await guard.enforce(tenant_id=TENANT_ID, namespace="gps") == 1
    assert await guard.enforce(tenant_id=TENANT_ID, namespace="gps") == 0
    with pytest.raises(RateLimitExceededError):
        await guard.enforce(tenant_id=TENANT_ID, namespace="gps")


@pytest.mark.asyncio
async def test_quotas_are_counted_per_service() -> None:
    guard = _guard({"requests_per_minute": 1})

    await guard.enforce(tenant_id=TENANT_ID, namespace="gps")
    # A different namespace has its own window.
    assert await guard.enforce(tenant_id=TENANT_ID, namespace="snmp") == 0
