"""API schemas for Authentication routes."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str = Field(
        ...,
        min_length=1,
        max_length=255,
        examples=["admin", "admin@lanstar.com.br"],
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
    access_token: str = ""
    token_type: str = "bearer"
    expires_in: int = 0
    user_id: UUID | None = None
    email: str = ""
    full_name: str = ""
    mfa_required: bool = False
    mfa_token: str | None = None


class MeResponse(BaseModel):
    """Identity + effective access — replaces the profile/role claims once in the JWT."""

    id: UUID
    email: str
    full_name: str
    tenant_id: UUID
    tenant_slug: str
    tenant_name: str = ""
    role_names: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    #: Services the principal can reach — the SPA hides whole slices with this.
    services: list[str] = Field(default_factory=list)
