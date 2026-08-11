"""Add users.credentials_version for access-token invalidation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_credentials_version"
down_revision = "0009_tenant_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "credentials_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "credentials_version")
