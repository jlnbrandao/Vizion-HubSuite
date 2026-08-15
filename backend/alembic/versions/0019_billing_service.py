"""Billing service catalog flag, entitlement row and tenant-scoped tables.

`tenant_only` marks product-tenant services that must never be attached to the
platform tenant (`ows`). Billing is mandatory for every other tenant.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0019_billing_service"
down_revision: str | None = "0018_service_core_flags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BILLING_TABLES = (
    "billing_customers",
    "billing_payment_methods",
    "billing_invoices",
    "billing_invoice_lines",
)

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


def _grant(table: str) -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vizion_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO vizion_app;
              END IF;
            END $$;
            """
        )
    )


def _protect(table: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_POLICY_SQL.format(table=table)))
    _grant(table)


def upgrade() -> None:
    op.add_column(
        "services",
        sa.Column(
            "tenant_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO services (
                id, slug, namespace, name, description, is_core, tenant_only, is_active
            )
            VALUES (
                gen_random_uuid(),
                'billing',
                'billing',
                'Billing',
                'Invoices and payments for contracted tenant services',
                false,
                true,
                true
            )
            ON CONFLICT (slug) DO UPDATE
            SET tenant_only = true,
                namespace = EXCLUDED.namespace,
                name = EXCLUDED.name,
                description = EXCLUDED.description
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO tenant_services (id, tenant_id, service_id, plan, status, activated_at)
            SELECT gen_random_uuid(), t.id, s.id, 'standard', 'active', now()
            FROM tenants t
            CROSS JOIN services s
            WHERE s.slug = 'billing'
              AND t.slug <> 'ows'
            ON CONFLICT (tenant_id, service_id) DO NOTHING
            """
        )
    )

    op.create_table(
        "billing_customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("asaas_customer_id", sa.String(64), nullable=True),
        sa.Column("legal_name", sa.String(150), nullable=False, server_default=""),
        sa.Column("email", sa.String(255), nullable=False, server_default=""),
        sa.Column("cpf_cnpj", sa.String(18), nullable=False, server_default=""),
        sa.Column("postal_code", sa.String(16), nullable=False, server_default=""),
        sa.Column("address", sa.String(200), nullable=False, server_default=""),
        sa.Column("address_number", sa.String(20), nullable=False, server_default=""),
        sa.Column("complement", sa.String(80), nullable=False, server_default=""),
        sa.Column("province", sa.String(80), nullable=False, server_default=""),
        sa.Column("city", sa.String(80), nullable=False, server_default=""),
        sa.Column("state", sa.String(2), nullable=False, server_default=""),
        sa.Column("country", sa.String(80), nullable=False, server_default="Brasil"),
        sa.Column("cycle_close_day", sa.Integer(), nullable=False, server_default="9"),
        sa.Column("alert_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("promo_code", sa.String(32), nullable=True),
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
        sa.UniqueConstraint("tenant_id", name="uq_billing_customers_tenant"),
        sa.CheckConstraint(
            "cycle_close_day IN (3, 6, 9)",
            name="ck_billing_customers_cycle_close_day",
        ),
    )

    op.create_table(
        "billing_payment_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("asaas_token", sa.String(128), nullable=True),
        sa.Column("billing_type", sa.String(24), nullable=False, server_default="CREDIT_CARD"),
        sa.Column("brand", sa.String(32), nullable=False, server_default=""),
        sa.Column("last4", sa.String(4), nullable=False, server_default=""),
        sa.Column("holder_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
    )

    op.create_table(
        "billing_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("asaas_payment_id", sa.String(64), nullable=True),
        sa.Column("invoice_url", sa.String(512), nullable=True),
        sa.Column("pix_payload", sa.String(512), nullable=True),
        sa.Column("description", sa.String(200), nullable=False, server_default=""),
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
        sa.CheckConstraint(
            "status IN ('draft','pending','paid','overdue','cancelled')",
            name="ck_billing_invoices_status",
        ),
    )

    op.create_table(
        "billing_invoice_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("billing_invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("ref", sa.String(64), nullable=True),
        sa.CheckConstraint(
            "kind IN ('user','service','discount')",
            name="ck_billing_invoice_lines_kind",
        ),
    )

    for table in _BILLING_TABLES:
        _protect(table)


def downgrade() -> None:
    for table in reversed(_BILLING_TABLES):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}"))
        op.drop_table(table)

    op.execute(
        sa.text(
            "DELETE FROM tenant_services WHERE service_id IN "
            "(SELECT id FROM services WHERE slug = 'billing')"
        )
    )
    op.execute(sa.text("DELETE FROM services WHERE slug = 'billing'"))
    op.drop_column("services", "tenant_only")
