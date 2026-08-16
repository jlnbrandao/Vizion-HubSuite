"""HTTP DTOs for Platform Core hub product APIs (`/api/v1/hub/...`)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class HubTokenRequest(BaseModel):
    client_id: str
    client_secret: str


class HubTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class IntrospectRequest(BaseModel):
    token: str


class PrincipalResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    tenant_id: UUID
    tenant_slug: str
    tenant_name: str = ""
    role_names: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class TenantResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    is_active: bool = True


class AuthorizeRequest(BaseModel):
    user_id: UUID
    tenant_id: UUID
    action: str
    resource_type: str | None = None
    resource_id: UUID | None = None


class AuthorizeResponse(BaseModel):
    allowed: bool
    reason: str = ""


class EntitlementCheckRequest(BaseModel):
    tenant_id: UUID
    capability: str


class EntitlementCheckResponse(BaseModel):
    entitled: bool


class HubAuditRequest(BaseModel):
    action: str
    user_id: UUID | None = None
    tenant_id: UUID | None = None
    resource_type: str | None = None
    resource_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HubEventRequest(BaseModel):
    event_type: str
    tenant_id: UUID
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class HeartbeatRequest(BaseModel):
    version: str
    status: str = "ok"
