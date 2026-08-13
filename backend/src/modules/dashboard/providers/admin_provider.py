"""ADMIN dashboard section — users, roles, permissions management only."""

from __future__ import annotations

from src.modules.dashboard.dtos.dashboard_dtos import DashboardMenuItem, DashboardWidget
from src.modules.dashboard.providers.base import DashboardSectionProvider
from src.modules.permissions.queries.permission_queries import CountPermissionsQuery
from src.modules.roles.queries.role_queries import CountRolesQuery
from src.modules.users.queries.user_queries import CountUsersQuery
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode


class AdminDashboardProvider(DashboardSectionProvider):
    def __init__(self, query_bus: QueryBus) -> None:
        self._query_bus = query_bus

    @property
    def required_permission(self) -> str:
        return PermissionCode.DASHBOARD_ADMIN

    async def build_menu(self, user: CurrentUser) -> list[DashboardMenuItem]:
        return [
            DashboardMenuItem(
                id="admin-overview",
                label="Administration",
                route="/admin",
                icon="admin_panel_settings",
                required_permission=PermissionCode.DASHBOARD_ADMIN,
            ),
            DashboardMenuItem(
                id="admin-users",
                label="Users",
                route="/users",
                icon="people",
                required_permission=PermissionCode.USERS_READ,
            ),
            DashboardMenuItem(
                id="admin-roles",
                label="Roles",
                route="/roles",
                icon="shield",
                required_permission=PermissionCode.ROLES_READ,
            ),
            DashboardMenuItem(
                id="admin-permissions",
                label="Permissions",
                route="/permissions",
                icon="key",
                required_permission=PermissionCode.PERMISSIONS_READ,
            ),
            DashboardMenuItem(
                id="admin-federation",
                label="Federation / SSO",
                route="/iam/federation",
                icon="login",
                required_permission=PermissionCode.FEDERATION_READ,
            ),
            DashboardMenuItem(
                id="admin-api-keys",
                label="API keys",
                route="/iam/api-keys",
                icon="vpn_key",
                required_permission=PermissionCode.API_KEYS_READ,
            ),
        ]

    async def build_widgets(self, user: CurrentUser) -> list[DashboardWidget]:
        users_total = await self._query_bus.ask(CountUsersQuery())
        users_active = await self._query_bus.ask(CountUsersQuery(only_active=True))
        roles_total = await self._query_bus.ask(CountRolesQuery())
        permissions_total = await self._query_bus.ask(CountPermissionsQuery())

        return [
            DashboardWidget(
                id="admin-rbac-stats",
                title="RBAC Administration",
                widget_type="stats",
                data={
                    "users_total": users_total,
                    "users_active": users_active,
                    "roles_total": roles_total,
                    "permissions_total": permissions_total,
                },
            ),
            DashboardWidget(
                id="admin-user-mgmt",
                title="Users",
                widget_type="actions",
                data={
                    "actions": [
                        {"label": "Create user", "route": "/users?create=1"},
                        {"label": "List users", "route": "/users"},
                    ]
                },
            ),
            DashboardWidget(
                id="admin-role-mgmt",
                title="Roles",
                widget_type="actions",
                data={
                    "actions": [
                        {"label": "Manage roles", "route": "/roles"},
                    ]
                },
            ),
            DashboardWidget(
                id="admin-permission-mgmt",
                title="Permissions",
                widget_type="actions",
                data={
                    "actions": [
                        {"label": "Manage permissions", "route": "/permissions"},
                    ]
                },
            ),
        ]
