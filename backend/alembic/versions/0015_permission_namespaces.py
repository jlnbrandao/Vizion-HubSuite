"""Permission namespaces (service.resource.action) and permission bundles.

Existing rows keep a single identity: `code` becomes the namespaced form and the
former `resource.action` value moves to `legacy_code`, which stays authoritative
for authorization until the aliases are dropped in a later, explicit step.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_permission_namespaces"
down_revision: str | None = "0014_resource_acls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GROUPS_TABLE = "permission_groups"
GROUP_ITEMS_TABLE = "permission_group_items"
ROLE_GROUPS_TABLE = "role_permission_groups"

# Frozen copy of SERVICE_BY_RESOURCE at this revision — migrations must not drift
# with the application catalog.
SERVICE_BY_RESOURCE: dict[str, str] = {
    "users": "iam",
    "roles": "iam",
    "permissions": "iam",
    "permission_groups": "iam",
    "dashboard": "iam",
    "system": "iam",
    "audit": "iam",
    "sessions": "iam",
    "oauth_clients": "iam",
    "service_accounts": "iam",
    "api_keys": "iam",
    "federation": "iam",
    "policies": "iam",
    "acl": "iam",
    "scim": "iam",
    "tenants": "platform",
    "services": "platform",
    "usage": "platform",
    "integration": "integration",
}

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

_GRANT_SQL = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vizion_app') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO vizion_app;
  END IF;
END $$;
"""


def _enable_rls(table: str) -> None:
    op.execute(sa.text(_GRANT_SQL.format(table=table)))
    op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_POLICY_SQL.format(table=table)))


def upgrade() -> None:
    op.add_column("permissions", sa.Column("legacy_code", sa.String(100), nullable=True))
    op.add_column("permissions", sa.Column("service", sa.String(32), nullable=True))
    op.create_index("ix_permissions_legacy_code", "permissions", ["legacy_code"])
    op.create_index("ix_permissions_service", "permissions", ["service"])

    _namespace_existing_permissions()

    op.create_table(
        GROUPS_TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("service", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint("tenant_id", "slug", name="uq_permission_groups_tenant_slug"),
    )

    op.create_table(
        GROUP_ITEMS_TABLE,
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{GROUPS_TABLE}.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    op.create_table(
        ROLE_GROUPS_TABLE,
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{GROUPS_TABLE}.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    for table in (GROUPS_TABLE, GROUP_ITEMS_TABLE, ROLE_GROUPS_TABLE):
        _enable_rls(table)


def _namespace_existing_permissions() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, code FROM permissions")).mappings().all()
    for row in rows:
        code = row["code"]
        parts = code.split(".")
        if len(parts) != 2:
            # Already namespaced (or malformed): only backfill the service.
            service = SERVICE_BY_RESOURCE.get(parts[0]) if len(parts) >= 3 else None
            if service:
                conn.execute(
                    sa.text("UPDATE permissions SET service = :service WHERE id = :id"),
                    {"service": service, "id": row["id"]},
                )
            continue

        resource = parts[0]
        service = SERVICE_BY_RESOURCE.get(resource)
        if service is None:
            # Custom permission outside the catalog: keep the code, no namespace.
            continue
        conn.execute(
            sa.text(
                """
                UPDATE permissions
                   SET code = :canonical, legacy_code = :legacy, service = :service
                 WHERE id = :id
                """
            ),
            {
                "canonical": f"{service}.{code}",
                "legacy": code,
                "service": service,
                "id": row["id"],
            },
        )


def downgrade() -> None:
    for table in (ROLE_GROUPS_TABLE, GROUP_ITEMS_TABLE, GROUPS_TABLE):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}"))
    op.drop_table(ROLE_GROUPS_TABLE)
    op.drop_table(GROUP_ITEMS_TABLE)
    op.drop_table(GROUPS_TABLE)

    op.execute(
        sa.text("UPDATE permissions SET code = legacy_code WHERE legacy_code IS NOT NULL")
    )
    op.drop_index("ix_permissions_service", table_name="permissions")
    op.drop_index("ix_permissions_legacy_code", table_name="permissions")
    op.drop_column("permissions", "service")
    op.drop_column("permissions", "legacy_code")
