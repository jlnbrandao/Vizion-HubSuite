"""Tighten tenants RLS, add resolve_tenant_by_slug, create least-privilege roles."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_tenant_security"
down_revision = "0008_tenants_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS tenants_select ON tenants"))
    op.execute(
        sa.text(
            """
            CREATE POLICY tenants_select ON tenants
              FOR SELECT
              USING (
                id::text = nullif(current_setting('app.current_tenant_id', true), '')
                OR current_setting('app.rls_bypass', true) = 'on'
              )
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION resolve_tenant_by_slug(p_slug text)
            RETURNS TABLE (
              id uuid,
              slug character varying(63),
              name character varying(120),
              is_active boolean,
              created_at timestamptz,
              updated_at timestamptz
            )
            LANGUAGE sql
            SECURITY DEFINER
            SET search_path = public
            STABLE
            AS $$
              SELECT t.id, t.slug, t.name, t.is_active, t.created_at, t.updated_at
              FROM tenants t
              WHERE t.slug = lower(trim(p_slug))
              LIMIT 1;
            $$
            """
        )
    )
    op.execute(sa.text("REVOKE ALL ON FUNCTION resolve_tenant_by_slug(text) FROM PUBLIC"))
    op.execute(sa.text("GRANT EXECUTE ON FUNCTION resolve_tenant_by_slug(text) TO PUBLIC"))

    # Least-privilege roles (dev defaults; rotate passwords in production).
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'vizion_app') THEN
                CREATE ROLE vizion_app LOGIN PASSWORD 'vizion_app' NOSUPERUSER NOBYPASSRLS;
              END IF;
              IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'vizion_migrate') THEN
                CREATE ROLE vizion_migrate LOGIN PASSWORD 'vizion_migrate'
                  NOSUPERUSER BYPASSRLS;
              END IF;
            END
            $$
            """
        )
    )
    op.execute(sa.text("GRANT CONNECT ON DATABASE vizion TO vizion_app, vizion_migrate"))
    op.execute(sa.text("GRANT USAGE ON SCHEMA public TO vizion_app, vizion_migrate"))
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
            "TO vizion_app, vizion_migrate"
        )
    )
    op.execute(
        sa.text(
            "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public "
            "TO vizion_app, vizion_migrate"
        )
    )
    op.execute(
        sa.text(
            "GRANT EXECUTE ON FUNCTION resolve_tenant_by_slug(text) "
            "TO vizion_app, vizion_migrate"
        )
    )
    op.execute(
        sa.text(
            """
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
              GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
              TO vizion_app, vizion_migrate
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP FUNCTION IF EXISTS resolve_tenant_by_slug(text)"))
    op.execute(sa.text("DROP POLICY IF EXISTS tenants_select ON tenants"))
    op.execute(
        sa.text("CREATE POLICY tenants_select ON tenants FOR SELECT USING (true)")
    )
    # Roles are left in place (safe for shared DBs); revoke optional.
