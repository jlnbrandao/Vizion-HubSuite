"""Dashboard composer tests — permission-driven sections, no role ifs."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.modules.dashboard.handlers.dashboard_handlers import GetDashboardHandler
from src.modules.dashboard.providers.admin_provider import AdminDashboardProvider
from src.modules.dashboard.providers.client_provider import ClientDashboardProvider
from src.modules.dashboard.providers.manager_provider import ManagerDashboardProvider
from src.modules.dashboard.providers.operator_provider import OperatorDashboardProvider
from src.modules.dashboard.providers.viewer_provider import ViewerDashboardProvider
from src.modules.dashboard.queries.dashboard_queries import GetDashboardQuery
from src.modules.dashboard.services.dashboard_composer import DashboardComposer
from src.modules.permissions.handlers.permission_handlers import CountPermissionsHandler
from src.modules.permissions.queries.permission_queries import CountPermissionsQuery
from src.modules.permissions.repositories.in_memory_permission_repository import (
    InMemoryPermissionRepository,
)
from src.modules.roles.handlers.role_handlers import CountRolesHandler
from src.modules.roles.queries.role_queries import CountRolesQuery
from src.modules.roles.repositories.in_memory_role_repository import InMemoryRoleRepository
from src.modules.users.entities.user import User
from src.modules.users.handlers.user_handlers import CountUsersHandler, GetUserByIdHandler
from src.modules.users.queries.user_queries import CountUsersQuery, GetUserByIdQuery
from src.modules.users.repositories.in_memory_user_repository import InMemoryUserRepository
from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.full_name import FullName
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.username import Username
from src.shared.application.event_bus import EventBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.security.permission_codes import PermissionCode
from tests.unit.conftest import BIGBANG_TENANT_ID
from tests.unit.shared.in_memory_unit_of_work import InMemoryUnitOfWork


@pytest.fixture
def uow_factory():
    bus = EventBus()

    def factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(bus)

    return factory


@pytest.fixture
def query_bus(uow_factory) -> QueryBus:
    users = InMemoryUserRepository()
    roles = InMemoryRoleRepository()
    permissions = InMemoryPermissionRepository()
    bus = QueryBus()
    bus.register(CountUsersQuery, CountUsersHandler(uow_factory, users))
    bus.register(CountRolesQuery, CountRolesHandler(uow_factory, roles))
    bus.register(CountPermissionsQuery, CountPermissionsHandler(uow_factory, permissions))
    bus.register(GetUserByIdQuery, GetUserByIdHandler(uow_factory, users))
    return bus


@pytest.fixture
def composer(query_bus: QueryBus) -> DashboardComposer:
    return DashboardComposer(
        [
            AdminDashboardProvider(query_bus),
            ManagerDashboardProvider(),
            OperatorDashboardProvider(),
            ClientDashboardProvider(query_bus),
            ViewerDashboardProvider(),
        ]
    )


@pytest.mark.asyncio
async def test_admin_dashboard_includes_rbac_sections(composer: DashboardComposer) -> None:
    handler = GetDashboardHandler(composer)
    result = await handler.handle(
        GetDashboardQuery(
            user_id=uuid4(),
            email="admin@lanstar.io",
            tenant_id=BIGBANG_TENANT_ID,
            tenant_slug="bigbang",
            full_name="Admin",
            role_names=frozenset({"ADMIN"}),
            permissions=frozenset(
                {
                    PermissionCode.DASHBOARD_ADMIN,
                    PermissionCode.USERS_READ,
                    PermissionCode.ROLES_READ,
                    PermissionCode.PERMISSIONS_READ,
                }
            ),
        )
    )

    widget_ids = {w.id for w in result.widgets}
    assert "admin-rbac-stats" in widget_ids
    assert "admin-user-mgmt" in widget_ids
    assert "admin-role-mgmt" in widget_ids
    assert "admin-permission-mgmt" in widget_ids
    assert "manager-kpis" not in widget_ids
    assert "admin-settings" not in widget_ids
    menu_ids = {m.id for m in result.menu}
    assert menu_ids == {
        "admin-overview",
        "admin-users",
        "admin-roles",
        "admin-permissions",
    }


@pytest.mark.asyncio
async def test_manager_and_viewer_compose_independently(composer: DashboardComposer) -> None:
    handler = GetDashboardHandler(composer)

    manager = await handler.handle(
        GetDashboardQuery(
            user_id=uuid4(),
            email="mgr@lanstar.io",
            tenant_id=BIGBANG_TENANT_ID,
            tenant_slug="bigbang",
            full_name="Manager",
            role_names=frozenset({"MANAGER"}),
            permissions=frozenset({PermissionCode.DASHBOARD_MANAGER}),
        )
    )
    assert {w.id for w in manager.widgets} == {"manager-kpis", "manager-reports"}

    viewer = await handler.handle(
        GetDashboardQuery(
            user_id=uuid4(),
            email="view@lanstar.io",
            tenant_id=BIGBANG_TENANT_ID,
            tenant_slug="bigbang",
            full_name="Viewer",
            role_names=frozenset({"VIEWER"}),
            permissions=frozenset({PermissionCode.DASHBOARD_VIEWER}),
        )
    )
    assert {w.id for w in viewer.widgets} == {"viewer-readonly"}
    assert viewer.widgets[0].widget_type == "readonly"


@pytest.mark.asyncio
async def test_operator_dashboard(composer: DashboardComposer) -> None:
    handler = GetDashboardHandler(composer)
    result = await handler.handle(
        GetDashboardQuery(
            user_id=uuid4(),
            email="op@lanstar.io",
            tenant_id=BIGBANG_TENANT_ID,
            tenant_slug="bigbang",
            full_name="Operator",
            permissions=frozenset({PermissionCode.DASHBOARD_OPERATOR}),
        )
    )
    assert result.widgets[0].id == "operator-today"
    assert "pending_tasks" in result.widgets[0].data


@pytest.mark.asyncio
async def test_client_dashboard_loads_own_profile(uow_factory, query_bus) -> None:
    users: InMemoryUserRepository = query_bus._handlers[GetUserByIdQuery]._users  # type: ignore[attr-defined]
    user = User.create(
        tenant_id=BIGBANG_TENANT_ID,
        email=Email(value="client@lanstar.io"),
        username=Username(value="client"),
        full_name=FullName(value="Client User"),
        hashed_password=HashedPassword(value="x" * 60),
    )
    await users.add(user)

    composer = DashboardComposer(
        [
            AdminDashboardProvider(query_bus),
            ManagerDashboardProvider(),
            OperatorDashboardProvider(),
            ClientDashboardProvider(query_bus),
            ViewerDashboardProvider(),
        ]
    )
    handler = GetDashboardHandler(composer)
    result = await handler.handle(
        GetDashboardQuery(
            user_id=user.id,
            email=user.email.value,
            tenant_id=BIGBANG_TENANT_ID,
            tenant_slug="bigbang",
            full_name=user.full_name.value,
            role_names=frozenset({"CLIENT"}),
            permissions=frozenset({PermissionCode.DASHBOARD_CLIENT}),
        )
    )

    assert len(result.widgets) == 1
    assert result.widgets[0].id == "client-own-data"
    assert result.widgets[0].data["email"] == "client@lanstar.io"


@pytest.mark.asyncio
async def test_no_dashboard_permissions_yields_empty(composer: DashboardComposer) -> None:
    handler = GetDashboardHandler(composer)
    result = await handler.handle(
        GetDashboardQuery(
            user_id=uuid4(),
            email="x@y.com",
            tenant_id=BIGBANG_TENANT_ID,
            tenant_slug="bigbang",
            full_name="Nobody",
            permissions=frozenset({PermissionCode.USERS_READ}),
        )
    )
    assert result.menu == ()
    assert result.widgets == ()
