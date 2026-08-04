"""Dashboard DTOs — menu + widgets composed per permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class DashboardMenuItem:
    id: str
    label: str
    route: str
    icon: str
    required_permission: str


@dataclass(frozen=True, kw_only=True)
class DashboardWidget:
    id: str
    title: str
    widget_type: str  # stats | indicators | operations | profile | readonly
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class DashboardDto:
    user_id: UUID
    email: str
    full_name: str
    role_names: tuple[str, ...] = field(default_factory=tuple)
    permissions: tuple[str, ...] = field(default_factory=tuple)
    menu: tuple[DashboardMenuItem, ...] = field(default_factory=tuple)
    widgets: tuple[DashboardWidget, ...] = field(default_factory=tuple)
