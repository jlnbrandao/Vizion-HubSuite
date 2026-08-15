"""Session denylist — revocation must outrank a still-valid access token."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.shared.infrastructure.security.session_denylist import InMemorySessionDenylist


@pytest.mark.asyncio
async def test_revoke_marks_only_the_target_session() -> None:
    denylist = InMemorySessionDenylist()
    revoked, kept = uuid4(), uuid4()

    await denylist.revoke(revoked)

    assert await denylist.is_revoked(revoked)
    assert not await denylist.is_revoked(kept)


@pytest.mark.asyncio
async def test_revoke_many_is_a_noop_for_empty_input() -> None:
    denylist = InMemorySessionDenylist()
    await denylist.revoke_many([])

    assert not await denylist.is_revoked(uuid4())


@pytest.mark.asyncio
async def test_revoke_many_marks_every_session() -> None:
    denylist = InMemorySessionDenylist()
    sessions = [uuid4() for _ in range(3)]

    await denylist.revoke_many(sessions)

    for session_id in sessions:
        assert await denylist.is_revoked(session_id)
