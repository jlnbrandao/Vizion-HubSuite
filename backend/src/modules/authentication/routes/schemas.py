"""API schemas for Authentication routes."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str = Field(
        ...,
        min_length=1,
        max_length=255,
        examples=["galileu", "galileu@lanstar.com.br"],
        description="Email or username",
    )
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    """Optional body token — prefers httpOnly cookie when omitted."""

    refresh_token: str | None = Field(default=None, min_length=32)


class LogoutRequest(BaseModel):
    """Optional body token — prefers httpOnly cookie when omitted."""

    refresh_token: str | None = Field(default=None, min_length=32)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: UUID
    email: str
    full_name: str
