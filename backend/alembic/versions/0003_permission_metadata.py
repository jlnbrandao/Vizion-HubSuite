"""Add resource and action columns to permissions for metadata filtering."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_permission_metadata"
down_revision: str | None = "0002_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "permissions",
        sa.Column("resource", sa.String(64), nullable=False, server_default=""),
    )
    op.add_column(
        "permissions",
        sa.Column("action", sa.String(64), nullable=False, server_default=""),
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, code FROM permissions")).mappings().all()
    for row in rows:
        code = row["code"]
        if "." in code:
            resource, action = code.split(".", 1)
        else:
            resource, action = code, ""
        conn.execute(
            sa.text(
                "UPDATE permissions SET resource = :resource, action = :action WHERE id = :id"
            ),
            {"resource": resource, "action": action, "id": row["id"]},
        )

    op.alter_column("permissions", "resource", server_default=None)
    op.alter_column("permissions", "action", server_default=None)
    op.create_index("ix_permissions_resource", "permissions", ["resource"])
    op.create_index("ix_permissions_action", "permissions", ["action"])


def downgrade() -> None:
    op.drop_index("ix_permissions_action", table_name="permissions")
    op.drop_index("ix_permissions_resource", table_name="permissions")
    op.drop_column("permissions", "action")
    op.drop_column("permissions", "resource")
