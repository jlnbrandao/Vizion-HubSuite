"""Add tenants, tenant_id columns, composite uniques, and FORCE RLS."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_tenants_rls"
down_revision: str | None = "0007_drop_navigation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIGBANG_ID = "a0000000-0000-4000-8000-000000000001"

TENANT_SCOPED_TABLES = (
    "permissions",
    "roles",
    "role_permissions",
    "users",
    "user_roles",
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


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    op.execute(
        sa.text(
            f"""
            INSERT INTO tenants (id, slug, name, is_active, created_at, updated_at)
            VALUES ('{BIGBANG_ID}'::uuid, 'bigbang', 'Bigbang', true, now(), now())
            """
        )
    )

    # --- permissions ---
    op.add_column(
        "permissions",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(sa.text(f"UPDATE permissions SET tenant_id = '{BIGBANG_ID}'"))
    op.alter_column("permissions", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_permissions_tenant_id",
        "permissions",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("uq_permissions_code", "permissions", type_="unique")
    op.drop_index("ix_permissions_code", table_name="permissions")
    op.create_unique_constraint(
        "uq_permissions_tenant_code", "permissions", ["tenant_id", "code"]
    )
    op.create_index("ix_permissions_tenant_code", "permissions", ["tenant_id", "code"])

    # --- roles ---
    op.add_column(
        "roles",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(sa.text(f"UPDATE roles SET tenant_id = '{BIGBANG_ID}'"))
    op.alter_column("roles", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_roles_tenant_id",
        "roles",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("uq_roles_name", "roles", type_="unique")
    op.drop_index("ix_roles_name", table_name="roles")
    op.create_unique_constraint("uq_roles_tenant_name", "roles", ["tenant_id", "name"])
    op.create_index("ix_roles_tenant_name", "roles", ["tenant_id", "name"])

    # --- users ---
    op.add_column(
        "users",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(sa.text(f"UPDATE users SET tenant_id = '{BIGBANG_ID}'"))
    op.alter_column("users", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_users_tenant_id",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_index("ix_users_username", table_name="users")
    op.create_unique_constraint("uq_users_tenant_email", "users", ["tenant_id", "email"])
    op.create_unique_constraint(
        "uq_users_tenant_username", "users", ["tenant_id", "username"]
    )
    op.create_index("ix_users_tenant_email", "users", ["tenant_id", "email"])
    op.create_index("ix_users_tenant_username", "users", ["tenant_id", "username"])

    # --- role_permissions ---
    op.add_column(
        "role_permissions",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        sa.text(
            f"""
            UPDATE role_permissions rp
            SET tenant_id = r.tenant_id
            FROM roles r
            WHERE r.id = rp.role_id
            """
        )
    )
    op.execute(
        sa.text(f"UPDATE role_permissions SET tenant_id = '{BIGBANG_ID}' WHERE tenant_id IS NULL")
    )
    op.alter_column("role_permissions", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_role_permissions_tenant_id",
        "role_permissions",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_role_permissions_tenant_id", "role_permissions", ["tenant_id"])

    # --- user_roles ---
    op.add_column(
        "user_roles",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE user_roles ur
            SET tenant_id = u.tenant_id
            FROM users u
            WHERE u.id = ur.user_id
            """
        )
    )
    op.execute(sa.text(f"UPDATE user_roles SET tenant_id = '{BIGBANG_ID}' WHERE tenant_id IS NULL"))
    op.alter_column("user_roles", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_user_roles_tenant_id",
        "user_roles",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_user_roles_tenant_id", "user_roles", ["tenant_id"])

    # --- RLS ---
    op.execute(sa.text("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE tenants FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text("CREATE POLICY tenants_select ON tenants FOR SELECT USING (true)")
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY tenants_write ON tenants
              FOR ALL
              USING (current_setting('app.rls_bypass', true) = 'on')
              WITH CHECK (current_setting('app.rls_bypass', true) = 'on')
            """
        )
    )

    for table in TENANT_SCOPED_TABLES:
        op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(_POLICY_SQL.format(table=table)))


def downgrade() -> None:
    for table in TENANT_SCOPED_TABLES:
        op.execute(sa.text(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}"))
        op.execute(sa.text(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    op.execute(sa.text("DROP POLICY IF EXISTS tenants_write ON tenants"))
    op.execute(sa.text("DROP POLICY IF EXISTS tenants_select ON tenants"))
    op.execute(sa.text("ALTER TABLE tenants NO FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY"))

    op.drop_index("ix_user_roles_tenant_id", table_name="user_roles")
    op.drop_constraint("fk_user_roles_tenant_id", "user_roles", type_="foreignkey")
    op.drop_column("user_roles", "tenant_id")

    op.drop_index("ix_role_permissions_tenant_id", table_name="role_permissions")
    op.drop_constraint("fk_role_permissions_tenant_id", "role_permissions", type_="foreignkey")
    op.drop_column("role_permissions", "tenant_id")

    op.drop_index("ix_users_tenant_username", table_name="users")
    op.drop_index("ix_users_tenant_email", table_name="users")
    op.drop_constraint("uq_users_tenant_username", "users", type_="unique")
    op.drop_constraint("uq_users_tenant_email", "users", type_="unique")
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_column("users", "tenant_id")
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_index("ix_users_username", "users", ["username"])

    op.drop_index("ix_roles_tenant_name", table_name="roles")
    op.drop_constraint("uq_roles_tenant_name", "roles", type_="unique")
    op.drop_constraint("fk_roles_tenant_id", "roles", type_="foreignkey")
    op.drop_column("roles", "tenant_id")
    op.create_unique_constraint("uq_roles_name", "roles", ["name"])
    op.create_index("ix_roles_name", "roles", ["name"])

    op.drop_index("ix_permissions_tenant_code", table_name="permissions")
    op.drop_constraint("uq_permissions_tenant_code", "permissions", type_="unique")
    op.drop_constraint("fk_permissions_tenant_id", "permissions", type_="foreignkey")
    op.drop_column("permissions", "tenant_id")
    op.create_unique_constraint("uq_permissions_code", "permissions", ["code"])
    op.create_index("ix_permissions_code", "permissions", ["code"])

    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")
