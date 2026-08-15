"""Resource ACLs — per-resource allow/deny exceptions (tenant-scoped RLS)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_resource_acls"
down_revision: str | None = "0013_integration_webhooks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "resource_acls"

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


def upgrade() -> None:
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
        sa.Column("subject_type", sa.String(16), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("effect", sa.String(8), nullable=False, server_default="allow"),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("effect IN ('allow','deny')", name="ck_resource_acls_effect"),
        sa.CheckConstraint(
            "subject_type IN ('user','role')", name="ck_resource_acls_subject_type"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "subject_type",
            "subject_id",
            "resource_type",
            "resource_id",
            "action",
            name="uq_resource_acls_entry",
        ),
    )
    # The engine looks entries up by tenant + resource + action on every check.
    op.create_index(
        "ix_resource_acls_lookup",
        TABLE,
        ["tenant_id", "resource_type", "resource_id", "action"],
    )
    op.create_index(
        "ix_resource_acls_subject",
        TABLE,
        ["tenant_id", "subject_type", "subject_id"],
    )
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vizion_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON {TABLE} TO vizion_app;
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
    op.drop_index("ix_resource_acls_subject", table_name=TABLE)
    op.drop_index("ix_resource_acls_lookup", table_name=TABLE)
    op.drop_table(TABLE)
