"""API request/response schemas for Roles routes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateRoleRequest(BaseModel):
    name: str = Field(..., examples=["ADMIN"])
    description: str = ""


class UpdateRoleRequest(BaseModel):
    description: str = ""
    is_active: bool = True


class PermissionIdsRequest(BaseModel):
    permission_ids: list[UUID]


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str
    permission_ids: list[UUID]
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RoleIdResponse(BaseModel):
    id: UUID
