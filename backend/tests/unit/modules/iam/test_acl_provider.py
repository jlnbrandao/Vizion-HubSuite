"""AclServiceProvider — how stored entries collapse into a single effect."""

from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest

from src.shared.infrastructure.security.authorization import AclEffect, ResourceRef
from src.shared.infrastructure.security.authorization_adapters import AclServiceProvider
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.session_context import bind_session, unbind_session


class FakeAclService:
    def __init__(self, effects: list[str]) -> None:
        self.effects = effects
        self.calls: list[dict[str, object]] = []

    async def effects_for(self, **kwargs: object) -> list[str]:
        self.calls.append(kwargs)
        return self.effects


@contextmanager
def _bound_session():
    """The provider abstains without a session; bind a dummy one."""
    token = bind_session(object())
    try:
        yield
    finally:
        unbind_session(token)


def _user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="u@x.com",
        full_name="User",
        tenant_id=uuid4(),
        tenant_slug="universe",
        role_ids=(uuid4(),),
    )


def _resource(resource_id: UUID | None = None) -> ResourceRef:
    return ResourceRef(type="vehicle", id=resource_id or uuid4())


@pytest.mark.asyncio
async def test_no_entries_means_no_opinion() -> None:
    provider = AclServiceProvider(FakeAclService([]))
    with _bound_session():
        assert await provider.effect_for(user=_user(), action="vehicle.read", resource=_resource()) is None


@pytest.mark.asyncio
async def test_single_allow_is_an_allow() -> None:
    provider = AclServiceProvider(FakeAclService(["allow"]))
    with _bound_session():
        effect = await provider.effect_for(
            user=_user(), action="vehicle.read", resource=_resource()
        )
    assert effect is AclEffect.ALLOW


@pytest.mark.asyncio
async def test_deny_wins_over_allow() -> None:
    provider = AclServiceProvider(FakeAclService(["allow", "deny"]))
    with _bound_session():
        effect = await provider.effect_for(
            user=_user(), action="vehicle.read", resource=_resource()
        )
    assert effect is AclEffect.DENY


@pytest.mark.asyncio
async def test_resource_without_id_is_not_looked_up() -> None:
    service = FakeAclService(["deny"])
    provider = AclServiceProvider(service)
    with _bound_session():
        effect = await provider.effect_for(
            user=_user(), action="vehicle.read", resource=ResourceRef(type="vehicle")
        )
    assert effect is None
    assert service.calls == []


@pytest.mark.asyncio
async def test_provider_abstains_without_a_db_session() -> None:
    service = FakeAclService(["deny"])
    provider = AclServiceProvider(service)

    effect = await provider.effect_for(
        user=_user(), action="vehicle.read", resource=_resource()
    )

    assert effect is None
    assert service.calls == []
