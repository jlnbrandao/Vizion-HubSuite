"""Usage records — the Accounting side of AAA.

One row per (tenant, service, metric, period). Counters are incremented in place,
so the table stays small enough to bill from and to show in the UI without a
warehouse.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base

GRANULARITY_DAY = "day"
GRANULARITY_MONTH = "month"
GRANULARITIES = frozenset({GRANULARITY_DAY, GRANULARITY_MONTH})


class UsageRecordModel(Base):
    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "service",
            "metric",
            "granularity",
            "period_start",
            name="uq_usage_records_period",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    #: Service namespace (`iam`, `integration`, `gps`, ...).
    service: Mapped[str] = mapped_column(String(32), nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    granularity: Mapped[str] = mapped_column(String(8), nullable=False, default=GRANULARITY_DAY)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
