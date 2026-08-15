"""Usage records (metering), audit `request_id` and audit retention helper.

Retention is a SQL function plus an index instead of a partitioned table: it keeps
the migration reversible and lets an operator (cron / pg_cron) call
`prune_audit_events(days)` without downtime. Partitioning becomes worthwhile only
once volume justifies it, and can be introduced later behind the same function.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017_usage_metering"
down_revision: str | None = "0016_service_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "usage_records"

_POLICY_SQL = """
CREATE POLICY {table}_tenant_isolation ON {table}
  FOR ALL
  USING (
    current_setting('app.rls_bypass', true) = 'on'
    OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
  )
  WITH CHECK (
    current_setting('app.rls_bypass', true) = 'on'
    OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
  )
"""

_PRUNE_FUNCTION = """
CREATE OR REPLACE FUNCTION prune_audit_events(retention_days integer)
RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
  removed bigint;
BEGIN
  IF retention_days IS NULL OR retention_days < 1 THEN
    RAISE EXCEPTION 'retention_days must be >= 1';
  END IF;
  DELETE FROM audit_events
   WHERE created_at < now() - make_interval(days => retention_days);
  GET DIAGNOSTICS removed = ROW_COUNT;
  RETURN removed;
END;
$$
"""


def upgrade() -> None:
    op.add_column(
        "audit_events", sa.Column("request_id", sa.String(64), nullable=True)
    )
    op.create_index(
        "ix_audit_events_request_id", "audit_events", ["tenant_id", "request_id"]
    )
    # Retention prunes by age; `ix_audit_events_created_at` (0011) already covers it.
    op.execute(sa.text(_PRUNE_FUNCTION))

    op.create_table(
        TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("service", sa.String(32), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("granularity", sa.String(8), nullable=False, server_default="day"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("granularity IN ('day','month')", name="ck_usage_records_granularity"),
        sa.CheckConstraint("quantity >= 0", name="ck_usage_records_quantity"),
        sa.UniqueConstraint(
            "tenant_id",
            "service",
            "metric",
            "granularity",
            "period_start",
            name="uq_usage_records_period",
        ),
    )
    op.create_index(
        "ix_usage_records_lookup",
        TABLE,
        ["tenant_id", "period_start", "service"],
    )
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vizion_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON {TABLE} TO vizion_app;
                GRANT EXECUTE ON FUNCTION prune_audit_events(integer) TO vizion_app;
              END IF;
            END $$;
            """
        )
    )
    op.execute(sa.text(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_POLICY_SQL.format(table=TABLE)))


def downgrade() -> None:
    op.execute(sa.text(f"DROP POLICY IF EXISTS {TABLE}_tenant_isolation ON {TABLE}"))
    op.drop_index("ix_usage_records_lookup", table_name=TABLE)
    op.drop_table(TABLE)
    op.execute(sa.text("DROP FUNCTION IF EXISTS prune_audit_events(integer)"))
    op.drop_index("ix_audit_events_request_id", table_name="audit_events")
    op.drop_column("audit_events", "request_id")
