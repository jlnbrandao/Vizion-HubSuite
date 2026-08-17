"""Let resolve_tenant_by_slug see tenants when the owner is not superuser.

FORCE RLS applies to the table owner. In Docker `vizion` is superuser so the
SECURITY DEFINER helper works; on a shared VPS it returns zero rows and login
fails with Unknown tenant.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023_resolve_tenant_rls_bypass"
down_revision: str | None = "0022_gis_service"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER FUNCTION resolve_tenant_by_slug(text) SET app.rls_bypass = 'on'"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER FUNCTION resolve_tenant_by_slug(text) RESET app.rls_bypass"))
