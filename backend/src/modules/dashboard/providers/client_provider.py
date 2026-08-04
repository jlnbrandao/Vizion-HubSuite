"""CLIENT dashboard section — only own profile data."""

from __future__ import annotations

from src.modules.dashboard.dtos.dashboard_dtos import DashboardMenuItem, DashboardWidget
from src.modules.dashboard.providers.base import DashboardSectionProvider
from src.modules.users.dtos.user_dtos import UserDto
from src.modules.users.queries.user_queries import GetUserByIdQuery
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode


class ClientDashboardProvider(DashboardSectionProvider):
    def __init__(self, query_bus: QueryBus) -> None:
        self._query_bus = query_bus

    @property
    def required_permission(self) -> str:
        return PermissionCode.DASHBOARD_CLIENT

    async def build_menu(self, user: CurrentUser) -> list[DashboardMenuItem]:
        return [
            DashboardMenuItem(
                id="client-profile",
                label="Meus dados",
                route="/me",
                icon="person",
                required_permission=PermissionCode.DASHBOARD_CLIENT,
            ),
        ]

    async def build_widgets(self, user: CurrentUser) -> list[DashboardWidget]:
        profile: UserDto = await self._query_bus.ask(GetUserByIdQuery(user_id=user.id))
        return [
            DashboardWidget(
                id="client-own-data",
                title="Meus dados",
                widget_type="profile",
                data={
                    "id": str(profile.id),
                    "email": profile.email,
                    "full_name": profile.full_name,
                    "is_active": profile.is_active,
                    "role_ids": [str(rid) for rid in profile.role_ids],
                },
            ),
        ]
