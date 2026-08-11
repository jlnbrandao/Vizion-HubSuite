"""Add ui_surface_bindings for page/component ↔ permission associations."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_ui_surface_bindings"
down_revision: str | None = "0005_dashboard_navigation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ui_surface_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("surface_key", sa.String(255), nullable=False),
        sa.Column(
            "assigned_permissions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
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
        sa.UniqueConstraint("surface_key", name="uq_ui_surface_bindings_key"),
    )
    op.create_index("ix_ui_surface_bindings_key", "ui_surface_bindings", ["surface_key"])


def downgrade() -> None:
    op.drop_index("ix_ui_surface_bindings_key", table_name="ui_surface_bindings")
    op.drop_table("ui_surface_bindings")
