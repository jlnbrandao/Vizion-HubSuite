"""API request/response schemas for Users routes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CreateUserRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=32, examples=["admin"])
    full_name: str = Field(..., min_length=2, max_length=150)
    password: str = Field(..., min_length=8, max_length=128)
    role_ids: list[UUID] = Field(default_factory=list)


class UpdateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    full_name: str = Field(..., min_length=2, max_length=150)
    is_active: bool = True


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)
    current_password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Required when changing your own password",
    )


class RoleIdsRequest(BaseModel):
    role_ids: list[UUID]


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    full_name: str
    role_ids: list[UUID]
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserIdResponse(BaseModel):
    id: UUID
