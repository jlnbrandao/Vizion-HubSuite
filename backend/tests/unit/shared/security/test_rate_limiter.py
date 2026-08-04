"""Unit tests for in-memory rate limiter."""

from __future__ import annotations

import pytest

from src.shared.infrastructure.security.rate_limiter import InMemoryRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_limit() -> None:
    limiter = InMemoryRateLimiter(limit=3, window_seconds=60)

    assert (await limiter.is_allowed("1.1.1.1")) == (True, 2)
    assert (await limiter.is_allowed("1.1.1.1")) == (True, 1)
    assert (await limiter.is_allowed("1.1.1.1")) == (True, 0)
    assert (await limiter.is_allowed("1.1.1.1")) == (False, 0)

    # Different IP has its own budget
    allowed, remaining = await limiter.is_allowed("2.2.2.2")
    assert allowed is True
    assert remaining == 2
