"""API schemas for Dashboard."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


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
    widgets: list[DashboardWidgetResponse]
