"""API schemas for Dashboard."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DashboardMenuItemResponse(BaseModel):
    id: str
    label: str
    route: str
    icon: str
    required_permission: str


class DashboardWidgetResponse(BaseModel):
    id: str
    title: str
    widget_type: str
    data: dict[str, Any]


class DashboardResponse(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    tenant_id: UUID | None = None
    tenant_slug: str = ""
    tenant_name: str = ""
    role_names: list[str]
    permissions: list[str]
    menu: list[DashboardMenuItemResponse]
    widgets: list[DashboardWidgetResponse]
