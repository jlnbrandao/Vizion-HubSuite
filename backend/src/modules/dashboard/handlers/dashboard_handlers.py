"""Dashboard query handler — delegates composition to DashboardComposer."""

from __future__ import annotations

from src.modules.dashboard.dtos.dashboard_dtos import DashboardDto
from src.modules.dashboard.queries.dashboard_queries import GetDashboardQuery
from src.modules.dashboard.services.dashboard_composer import DashboardComposer
from src.shared.application.handler import QueryHandler
from src.shared.infrastructure.security.current_user import CurrentUser


class GetDashboardHandler(QueryHandler[GetDashboardQuery, DashboardDto]):
    def __init__(self, composer: DashboardComposer) -> None:
        self._composer = composer

    async def handle(self, query: GetDashboardQuery) -> DashboardDto:
        user = CurrentUser(
            id=query.user_id,
            email=query.email,
            full_name=query.full_name,
            role_ids=query.role_ids,
            role_names=query.role_names,
            permissions=query.permissions,
        )
        return await self._composer.compose(user)
