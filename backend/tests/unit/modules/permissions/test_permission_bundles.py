"""Bundle-derived codes reach the effective access set of a role."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.modules.authentication.handlers.access_handlers import ResolveEffectiveAccessHandler
from src.modules.authentication.queries.access_queries import ResolveEffectiveAccessQuery
from src.modules.permissions.handlers.permission_group_handlers import (
    ResolveRoleBundleCodesHandler,
)
from src.modules.permissions.queries.permission_group_queries import (
    ResolveRoleBundleCodesQuery,
)
from src.modules.roles.commands.role_commands import CreateRoleCommand
from src.modules.roles.handlers.role_handlers import CreateRoleHandler, GetRolesByIdsHandler
from src.modules.roles.queries.role_queries import GetRolesByIdsQuery
from src.modules.roles.repositories.in_memory_role_repository import InMemoryRoleRepository
from src.shared.application.event_bus import EventBus
from src.shared.application.query_bus import QueryBus
from tests.unit.conftest import UNIVERSE_TENANT_ID
from tests.unit.shared.in_memory_unit_of_work import InMemoryUnitOfWork


class FakeGroupService:
    """Stands in for the SQL bundle store: role → codes, already expanded."""

    def __init__(self, codes: frozenset[str]) -> None:
        self._codes = codes
        self.calls: list[frozenset] = []

    async def codes_for_roles(self, role_ids: frozenset) -> frozenset[str]:
        self.calls.append(role_ids)
        return self._codes


@pytest.fixture
def uow_factory():
    bus = EventBus()

    def factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(bus)

    return factory


@pytest.mark.asyncio
async def test_role_inherits_codes_from_bundles(uow_factory) -> None:
    roles_repo = InMemoryRoleRepository()
    query_bus = QueryBus()
    groups = FakeGroupService(frozenset({"iam.users.read"}))

    query_bus.register(GetRolesByIdsQuery, GetRolesByIdsHandler(uow_factory, roles_repo))
    query_bus.register(
        ResolveRoleBundleCodesQuery,
        ResolveRoleBundleCodesHandler(uow_factory, groups),
    )

    role_id = await CreateRoleHandler(uow_factory, roles_repo).handle(
        CreateRoleCommand(tenant_id=UNIVERSE_TENANT_ID, name="SUPPORT")
    )

    access = await ResolveEffectiveAccessHandler(query_bus).handle(
        ResolveEffectiveAccessQuery(role_ids=frozenset({role_id}))
    )

    # The role has no direct permissions — everything comes from the bundle,
    # and both code forms authorize.
    assert "iam.users.read" in access.permission_codes
    assert "users.read" in access.permission_codes
    assert groups.calls == [frozenset({role_id})]


@pytest.mark.asyncio
async def test_no_bundles_means_no_extra_codes(uow_factory) -> None:
    roles_repo = InMemoryRoleRepository()
    query_bus = QueryBus()
    groups = FakeGroupService(frozenset())

    query_bus.register(GetRolesByIdsQuery, GetRolesByIdsHandler(uow_factory, roles_repo))
    query_bus.register(
        ResolveRoleBundleCodesQuery,
        ResolveRoleBundleCodesHandler(uow_factory, groups),
    )

    role_id = await CreateRoleHandler(uow_factory, roles_repo).handle(
        CreateRoleCommand(tenant_id=UNIVERSE_TENANT_ID, name="EMPTY")
    )

    access = await ResolveEffectiveAccessHandler(query_bus).handle(
        ResolveEffectiveAccessQuery(role_ids=frozenset({role_id}))
    )

    assert access.permission_codes == frozenset()
    assert access.role_names == frozenset({"EMPTY"})


@pytest.mark.asyncio
async def test_bundle_handler_short_circuits_without_roles(uow_factory) -> None:
    groups = FakeGroupService(frozenset({"iam.users.read"}))
    handler = ResolveRoleBundleCodesHandler(uow_factory, groups)

    assert await handler.handle(ResolveRoleBundleCodesQuery(role_ids=frozenset())) == frozenset()
    assert groups.calls == []


@pytest.mark.asyncio
async def test_unknown_role_ids_are_not_invented(uow_factory) -> None:
    roles_repo = InMemoryRoleRepository()
    query_bus = QueryBus()
    query_bus.register(GetRolesByIdsQuery, GetRolesByIdsHandler(uow_factory, roles_repo))
    query_bus.register(
        ResolveRoleBundleCodesQuery,
        ResolveRoleBundleCodesHandler(uow_factory, FakeGroupService(frozenset())),
    )

    access = await ResolveEffectiveAccessHandler(query_bus).handle(
        ResolveEffectiveAccessQuery(role_ids=frozenset({uuid4()}))
    )

    assert access.role_names == frozenset()
    assert access.permission_codes == frozenset()
