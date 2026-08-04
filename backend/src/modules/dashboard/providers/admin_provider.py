"""ADMIN dashboard section — system stats, user management, settings."""

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
                id="admin-users",
                label="Gerenciamento de usuários",
                route="/users",
                icon="people",
                required_permission=PermissionCode.USERS_READ,
            ),
            DashboardMenuItem(
                id="admin-roles",
                label="Roles e permissões",
                route="/roles",
                icon="shield",
                required_permission=PermissionCode.ROLES_READ,
            ),
            DashboardMenuItem(
                id="admin-settings",
                label="Configurações",
                route="/settings",
                icon="settings",
                required_permission=PermissionCode.SYSTEM_SETTINGS,
            ),
        ]

    async def build_widgets(self, user: CurrentUser) -> list[DashboardWidget]:
        users_total = await self._query_bus.ask(CountUsersQuery())
        users_active = await self._query_bus.ask(CountUsersQuery(only_active=True))
        roles_total = await self._query_bus.ask(CountRolesQuery())
        permissions_total = await self._query_bus.ask(CountPermissionsQuery())

        return [
            DashboardWidget(
                id="admin-system-stats",
                title="Estatísticas do sistema",
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
                title="Gerenciamento de usuários",
                widget_type="actions",
                data={
                    "actions": [
                        {"label": "Criar usuário", "route": "/users/new"},
                        {"label": "Listar usuários", "route": "/users"},
                    ]
                },
            ),
            DashboardWidget(
                id="admin-settings",
                title="Configurações",
                widget_type="actions",
                data={
                    "actions": [
                        {"label": "Abrir configurações", "route": "/settings"},
                    ]
                },
            ),
        ]
