from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class ProductInstanceModel(Base):
    """Registered deployment of a distributable product. Platform-global."""

    __tablename__ = "product_instances"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    ui_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="registered")
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    client_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    environment: Mapped[str] = mapped_column(
        String(32), nullable=False, default="local_docker"
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    api_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ui_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ui_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scheme: Mapped[str] = mapped_column(String(8), nullable=False, default="http")
    notes: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class TenantProductBindingModel(Base):
    __tablename__ = "tenant_product_bindings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "product_instance_id",
            name="uq_tenant_product_instance",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_instance_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("product_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_slug: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
