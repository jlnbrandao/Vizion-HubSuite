"""API request/response schemas for Permissions routes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreatePermissionRequest(BaseModel):
    code: str = Field(..., examples=["users.create"])
    name: str = Field(..., examples=["Create User"])
    description: str = ""


class UpdatePermissionRequest(BaseModel):
    name: str
    description: str = ""
    is_active: bool = True


class PermissionResponse(BaseModel):
    id: UUID
    code: str
    resource: str
    action: str
    name: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PermissionIdResponse(BaseModel):
    id: UUID
