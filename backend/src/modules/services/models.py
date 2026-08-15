"""ORM models for the service catalog and per-tenant entitlements.

`services` is a platform-wide catalog (no tenant column, no RLS): it describes
what the Hub can offer. `tenant_services` is the contract of one tenant with one
service and is tenant-scoped with RLS, like every other tenant table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base

#: Lifecycle of a tenant × service contract. Only ACTIVE and TRIAL authorize.
STATUS_ACTIVE = "active"
STATUS_TRIAL = "trial"
STATUS_SUSPENDED = "suspended"
STATUS_DISABLED = "disabled"

ENTITLED_STATUSES = frozenset({STATUS_ACTIVE, STATUS_TRIAL})
TENANT_SERVICE_STATUSES = frozenset(
    {STATUS_ACTIVE, STATUS_TRIAL, STATUS_SUSPENDED, STATUS_DISABLED}
)


class ServiceModel(Base):
    __tablename__ = "services"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    #: Permission namespace owned by the service (`iam`, `gps`, ...).
    namespace: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    #: Core services are part of the Hub itself and cannot be sold or disabled.
    is_core: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_quotas: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class TenantServiceModel(Base):
    __tablename__ = "tenant_services"
    __table_args__ = (
        UniqueConstraint("tenant_id", "service_id", name="uq_tenant_services_tenant_service"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_ACTIVE)
    #: Per-tenant overrides merged over `services.default_quotas`.
    quotas: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
