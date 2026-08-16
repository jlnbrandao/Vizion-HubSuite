"""Product instance registry for distributable OpenVizion products."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0020_product_instances"
down_revision: str | None = "0019_billing_service"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PRODUCTS = (
    ("tracking", "tracking", "Tracking", "GPS tracking product — devices, positions, geofences"),
    ("iot", "iot", "IoT", "IoT product scaffold"),
    ("snmp", "snmp", "SNMP", "SNMP product scaffold"),
)


def upgrade() -> None:
    op.create_table(
        "product_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=False),
        sa.Column("ui_url", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="registered"),
        sa.Column("version", sa.String(64), nullable=False, server_default=""),
        sa.Column("client_id", sa.String(64), nullable=False, unique=True),
        sa.Column("client_secret_hash", sa.String(255), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_product_instances_slug", "product_instances", ["slug"])
    op.create_table(
        "tenant_product_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_instance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("service_slug", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.UniqueConstraint("tenant_id", "product_instance_id", name="uq_tenant_product_instance"),
    )
    op.execute(sa.text("ALTER TABLE tenant_product_bindings ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE tenant_product_bindings FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            """
            CREATE POLICY tenant_product_bindings_isolation ON tenant_product_bindings
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
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vizion_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON product_instances TO vizion_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_product_bindings TO vizion_app;
              END IF;
            END $$;
            """
        )
    )
    for slug, namespace, name, description in _PRODUCTS:
        op.execute(
            sa.text(
                f"""
                INSERT INTO services (id, slug, namespace, name, description, is_core, tenant_only, is_active)
                VALUES (
                    gen_random_uuid(),
                    '{slug}',
                    '{namespace}',
                    '{name}',
                    '{description}',
                    false,
                    true,
                    true
                )
                ON CONFLICT (slug) DO UPDATE
                SET namespace = EXCLUDED.namespace,
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    tenant_only = true
                """
            )
        )


def downgrade() -> None:
    op.drop_table("tenant_product_bindings")
    op.drop_table("product_instances")
