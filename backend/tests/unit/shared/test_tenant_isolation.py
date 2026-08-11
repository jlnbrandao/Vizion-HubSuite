"""Cross-tenant isolation helpers for in-memory repositories."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.modules.users.entities.user import User
from src.modules.users.repositories.in_memory_user_repository import InMemoryUserRepository
from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.full_name import FullName
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.username import Username
from src.shared.infrastructure.tenant_context import bind_tenant, unbind_tenant
from tests.unit.conftest import BIGBANG_TENANT_ID

OTHER_TENANT_ID = uuid4()


def _user(*, tenant_id, email: str, username: str) -> User:
    return User.create(
        tenant_id=tenant_id,
        email=Email.from_primitive(email),
        username=Username.from_primitive(username),
        full_name=FullName.from_primitive("Test User"),
        hashed_password=HashedPassword(value="hashed::x::" + ("y" * 40)),
    )


@pytest.mark.asyncio
async def test_in_memory_user_get_by_id_is_tenant_scoped() -> None:
    repo = InMemoryUserRepository()
    local = _user(tenant_id=BIGBANG_TENANT_ID, email="a@x.com", username="local")
    foreign = _user(tenant_id=OTHER_TENANT_ID, email="b@x.com", username="foreign")
    await repo.add(local)
    await repo.add(foreign)

    # Autouse fixture binds BIGBANG
    assert await repo.get_by_id(local.id) is not None
    assert await repo.get_by_id(foreign.id) is None

    tokens = bind_tenant(OTHER_TENANT_ID, slug="other", name="Other")
    try:
        assert await repo.get_by_id(foreign.id) is not None
        assert await repo.get_by_id(local.id) is None
    finally:
        unbind_tenant(*tokens)
