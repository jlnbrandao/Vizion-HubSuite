"""Composes dashboard widgets from registered section providers.

Navigation is not composed here: the shell menu comes from
`src/modules/navigation`, so an entry is declared in exactly one place.
"""

from __future__ import annotations

from collections.abc import Sequence

from src.modules.dashboard.dtos.dashboard_dtos import DashboardDto, DashboardWidget
from src.modules.dashboard.providers.base import DashboardSectionProvider
from src.shared.infrastructure.security.current_user import CurrentUser


class DashboardComposer:
    def __init__(self, providers: Sequence[DashboardSectionProvider]) -> None:
        self._providers = tuple(providers)

    async def compose(self, user: CurrentUser) -> DashboardDto:
        widgets: list[DashboardWidget] = []

        for provider in self._providers:
            if not user.has_permission(provider.required_permission):
                continue
            widgets.extend(await provider.build_widgets(user))

        return DashboardDto(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            tenant_id=user.tenant_id,
            tenant_slug=user.tenant_slug,
            tenant_name=user.tenant_name,
            role_names=tuple(sorted(user.role_names)),
            permissions=tuple(sorted(user.permissions)),
            widgets=tuple(widgets),
        )
