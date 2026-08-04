"""Dashboard section provider contract — Strategy / Open-Closed.

Each provider is gated by a single dashboard.* permission.
The composer activates providers the CurrentUser is allowed to see.
No role-name branching in the handler.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.modules.dashboard.dtos.dashboard_dtos import DashboardMenuItem, DashboardWidget
from src.shared.infrastructure.security.current_user import CurrentUser


class DashboardSectionProvider(ABC):
    @property
    @abstractmethod
    def required_permission(self) -> str:
        """Permission code that unlocks this section (e.g. dashboard.admin)."""

    @abstractmethod
    async def build_menu(self, user: CurrentUser) -> list[DashboardMenuItem]:
        ...

    @abstractmethod
    async def build_widgets(self, user: CurrentUser) -> list[DashboardWidget]:
        ...
