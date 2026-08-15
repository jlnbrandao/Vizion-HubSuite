"""Per-tenant, per-service quotas enforced on the existing Redis limiter.

A service slice calls `enforce()` at the entry point of a metered operation. The
limit comes from `tenant_services.quotas` merged over `services.default_quotas`,
so plans are data, not code:

    {"requests_per_minute": 600, "sync_per_hour": 20}

A metric absent from the merged quotas is unlimited.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from time import monotonic
from typing import Any
from uuid import UUID

from src.modules.services.service import ServiceCatalogService
from src.modules.services.usage import UsageService
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.exceptions import RateLimitExceededError
from src.shared.infrastructure.security.rate_limiter import RateLimiter
from src.shared.infrastructure.session_context import get_current_session

UowFactory = Callable[[], AbstractAsyncContextManager[UnitOfWork]]

#: Default metric of a metered request, one fixed window of 60s.
REQUESTS_PER_MINUTE = "requests_per_minute"


class ServiceQuotaGuard:
    def __init__(
        self,
        catalog: ServiceCatalogService,
        rate_limiter: RateLimiter,
        uow_factory: UowFactory,
        usage: UsageService | None = None,
        ttl_seconds: int = 30,
    ) -> None:
        self._catalog = catalog
        self._limiter = rate_limiter
        self._uow_factory = uow_factory
        self._usage = usage
        self._ttl = ttl_seconds
        self._cache: dict[tuple[UUID, str, str], tuple[float, int | None]] = {}

    async def enforce(
        self,
        *,
        tenant_id: UUID,
        namespace: str,
        metric: str = REQUESTS_PER_MINUTE,
        window_seconds: int = 60,
        meter: bool = True,
    ) -> int:
        """Consume one unit of a quota and return the remaining allowance.

        -1 means unlimited. Raises `RateLimitExceededError` when the window is
        exhausted. Accepted calls are metered, including unlimited ones — billing
        needs the count even when there is no ceiling.
        """
        limit = await self._limit(tenant_id, namespace, metric)
        if limit is not None:
            allowed, remaining = await self._limiter.is_allowed(
                f"svc:{tenant_id}:{namespace}:{metric}",
                limit=limit,
                window_seconds=window_seconds,
            )
            if not allowed:
                raise RateLimitExceededError(
                    f"Quota exceeded for {namespace}.{metric} ({limit} per {window_seconds}s)"
                )
        else:
            remaining = -1

        if meter:
            await self._meter(tenant_id=tenant_id, namespace=namespace, metric=metric)
        return remaining

    async def _meter(self, *, tenant_id: UUID, namespace: str, metric: str) -> None:
        """Persist one usage unit in its own transaction.

        Metering is independent of the caller's transaction on purpose: the quota
        unit was consumed even if the operation itself later rolls back.
        """
        if self._usage is None:
            return
        async with self._uow_factory() as uow:
            await self._usage.record(
                tenant_id=tenant_id, service=namespace, metric=metric
            )
            await uow.commit()

    def invalidate(self, tenant_id: UUID | None = None) -> None:
        if tenant_id is None:
            self._cache.clear()
            return
        for key in [k for k in self._cache if k[0] == tenant_id]:
            self._cache.pop(key, None)

    async def _limit(self, tenant_id: UUID, namespace: str, metric: str) -> int | None:
        cache_key = (tenant_id, namespace, metric)
        now = monotonic()
        cached = self._cache.get(cache_key)
        if cached is not None and cached[0] > now:
            return cached[1]

        limit = await self._read_limit(tenant_id, namespace, metric)
        self._cache[cache_key] = (now + self._ttl, limit)
        return limit

    async def _read_limit(self, tenant_id: UUID, namespace: str, metric: str) -> int | None:
        async def read() -> Any:
            return await self._catalog.quota(
                tenant_id=tenant_id, namespace=namespace, key=metric
            )

        try:
            get_current_session()
        except RuntimeError:
            async with self._uow_factory():
                return await read()
        return await read()
