"""Service catalog (`services`) and per-tenant entitlements (`tenant_services`).

`services` is platform-wide: readable by anyone authenticated, writable only with
the RLS bypass used by platform administration. `tenant_services` follows the
regular tenant isolation policy.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_service_catalog"
down_revision: str | None = "0015_permission_namespaces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_POLICY_SQL = """
CREATE POLICY tenant_services_tenant_isolation ON tenant_services
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

#: Services that already exist as modules in this repository.
_CORE_SERVICES = (
    ("iam", "iam", "Identity & Access", "Users, roles, permissions, MFA, sessions, audit"),
    ("platform", "platform", "Platform", "Tenant catalog and cross-tenant administration"),
    ("integration", "integration", "Integration Hub", "Outbound integrations and webhooks"),
)


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


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(32), nullable=False),
        sa.Column("namespace", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(255), nullable=False, server_default=""),
        sa.Column("version", sa.String(16), nullable=False, server_default="1.0"),
        sa.Column("is_core", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "default_quotas",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
        sa.UniqueConstraint("slug", name="uq_services_slug"),
        sa.UniqueConstraint("namespace", name="uq_services_namespace"),
    )

    op.create_table(
        "tenant_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("plan", sa.String(32), nullable=False, server_default="standard"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column(
            "quotas", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('active','trial','suspended','disabled')",
            name="ck_tenant_services_status",
        ),
        sa.UniqueConstraint(
            "tenant_id", "service_id", name="uq_tenant_services_tenant_service"
        ),
    )
    op.create_index(
        "ix_tenant_services_lookup", "tenant_services", ["tenant_id", "service_id", "status"]
    )

    for slug, namespace, name, description in _CORE_SERVICES:
        op.execute(
            sa.text(
                """
                INSERT INTO services (id, slug, namespace, name, description, is_core)
                VALUES (gen_random_uuid(), :slug, :namespace, :name, :description, true)
                ON CONFLICT (slug) DO NOTHING
                """
            ).bindparams(slug=slug, namespace=namespace, name=name, description=description)
        )

    # Existing tenants keep working: entitle every tenant to the core services.
    op.execute(
        sa.text(
            """
            INSERT INTO tenant_services (id, tenant_id, service_id, plan, status, activated_at)
            SELECT gen_random_uuid(), t.id, s.id, 'standard', 'active', now()
            FROM tenants t
            CROSS JOIN services s
            WHERE s.is_core
            ON CONFLICT (tenant_id, service_id) DO NOTHING
            """
        )
    )

    _grant("services")
    _grant("tenant_services")

    op.execute(sa.text("ALTER TABLE services ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE services FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text("CREATE POLICY services_select ON services FOR SELECT USING (true)"))
    op.execute(
        sa.text(
            """
            CREATE POLICY services_write ON services
              FOR ALL
              USING (current_setting('app.rls_bypass', true) = 'on')
              WITH CHECK (current_setting('app.rls_bypass', true) = 'on')
            """
        )
    )

    op.execute(sa.text("ALTER TABLE tenant_services ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE tenant_services FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_TENANT_POLICY_SQL))


def downgrade() -> None:
    op.execute(
        sa.text("DROP POLICY IF EXISTS tenant_services_tenant_isolation ON tenant_services")
    )
    op.execute(sa.text("DROP POLICY IF EXISTS services_write ON services"))
    op.execute(sa.text("DROP POLICY IF EXISTS services_select ON services"))
    op.drop_index("ix_tenant_services_lookup", table_name="tenant_services")
    op.drop_table("tenant_services")
    op.drop_table("services")
