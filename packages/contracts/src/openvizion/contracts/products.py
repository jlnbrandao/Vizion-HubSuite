"""Product instance registry contracts (orchestration UI + admin API)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

ProductSlug = Literal["tracking", "iot", "snmp", "gis"]
PRODUCT_SLUGS: tuple[str, ...] = ("tracking", "iot", "snmp", "gis")


class ProductInstance(BaseModel):
    id: UUID
    slug: ProductSlug
    name: str
    base_url: HttpUrl
    ui_url: HttpUrl | None = None
    status: str = "registered"
    version: str = ""
    last_heartbeat_at: datetime | None = None
    client_id: str
    environment: str = "local_docker"
    host: str = ""
    api_port: int | None = None
    notes: str = ""


class ProductBinding(BaseModel):
    tenant_id: UUID
    product_instance_id: UUID
    service_slug: str
    status: str = "active"


class CreateProductInstanceRequest(BaseModel):
    slug: ProductSlug
    name: str
    client_id: str
    client_secret: str = Field(min_length=16)
    environment: str = "local_docker"
    host: str = ""
    api_port: int | None = None
    ui_host: str | None = None
    ui_port: int | None = None
    scheme: str = "http"
    base_url: str = ""
    ui_url: str | None = None
    notes: str = ""


class UpdateProductInstanceRequest(BaseModel):
    name: str | None = None
    environment: str | None = None
    host: str | None = None
    api_port: int | None = None
    ui_host: str | None = None
    ui_port: int | None = None
    scheme: str | None = None
    base_url: str | None = None
    ui_url: str | None = None
    notes: str | None = None
    status: str | None = None
    client_secret: str | None = None


class BindTenantRequest(BaseModel):
    tenant_id: UUID
    status: str = "active"
