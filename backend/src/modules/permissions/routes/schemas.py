"""API request/response schemas for Permissions routes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreatePermissionRequest(BaseModel):
    code: str = Field(..., examples=["iam.users.create"])
    name: str = Field(..., examples=["Create User"])
    description: str = ""


class UpdatePermissionRequest(BaseModel):
    name: str
    description: str = ""
    is_active: bool = True


class PermissionResponse(BaseModel):
    id: UUID
    code: str
    legacy_code: str | None = None
    service: str | None = None
    resource: str
    action: str
    name: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PermissionIdResponse(BaseModel):
    id: UUID


class PermissionCatalogEntry(BaseModel):
    """Canonical catalog entry — source of truth for the generated frontend copy."""

    code: str
    legacy_code: str
    service: str
    resource: str
    action: str
    name: str
    description: str


class PermissionBundleResponse(BaseModel):
    id: UUID
    slug: str
    service: str
    name: str
    description: str
    is_active: bool
    permission_ids: list[UUID] = Field(default_factory=list)
    permission_codes: list[str] = Field(default_factory=list)


class UpsertPermissionBundleRequest(BaseModel):
    slug: str = Field(..., examples=["iam.admin"])
    service: str = Field(..., examples=["iam"])
    name: str = Field(..., examples=["IAM administration"])
    description: str = ""
    permission_ids: list[UUID] = Field(default_factory=list)


class RoleBundlesRequest(BaseModel):
    group_ids: list[UUID] = Field(default_factory=list)
