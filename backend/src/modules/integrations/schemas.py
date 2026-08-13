"""Pydantic schemas for Integration Hub HTTP API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

IntegrationType = Literal[
    "rest",
    "oauth2",
    "mtls",
    "webhook",
    "sftp",
    "http_file",
    "soap",
    "incremental_sync",
    "database",
]

IntegrationStatus = Literal[
    "ACTIVE",
    "INACTIVE",
    "ERROR",
    "TESTING",
    "SYNCING",
    "NEVER_SYNCED",
]


class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str
    type: str
    status: str
    configuration: dict[str, Any]
    secrets_configured: bool
    created_at: datetime
    updated_at: datetime
    last_sync_at: datetime | None = None
    last_error: str | None = None


class CreateIntegrationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str = ""
    type: IntegrationType
    status: IntegrationStatus = "NEVER_SYNCED"
    configuration: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, Any] | None = None


class UpdateIntegrationRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    status: IntegrationStatus | None = None
    configuration: dict[str, Any] | None = None
    secrets: dict[str, Any] | None = None


class IntegrationTestResponse(BaseModel):
    success: bool
    message: str
    server: str | None = None
    duration_ms: int | None = None
    authentication: str | None = None
    permission: str | None = None
    error_detail: str | None = None


class IntegrationSyncResponse(BaseModel):
    success: bool
    mode: str
    records_processed: int
    message: str
    started_at: str
    finished_at: str
    cursor_value: str | None = None


class IntegrationStatusResponse(BaseModel):
    id: UUID
    status: str
    last_sync_at: datetime | None = None
    last_error: str | None = None


class IntegrationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    integration_id: UUID
    level: str
    message: str
    created_at: datetime


class WebhookReceiveResponse(BaseModel):
    accepted: bool
    duplicate: bool = False
    event_type: str | None = None
    delivery_id: UUID | None = None
    message: str
