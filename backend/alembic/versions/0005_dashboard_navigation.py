"""Add dashboard_menu_items and dashboard_widgets tables."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_dashboard_navigation"
down_revision: str | None = "0004_users_username"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dashboard_menu_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("route", sa.String(255), nullable=False),
        sa.Column("icon", sa.String(64), nullable=False, server_default="circle"),
        sa.Column("section", sa.String(100), nullable=False),
        sa.Column("required_permission", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
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
        sa.UniqueConstraint("key", name="uq_dashboard_menu_items_key"),
    )
    op.create_index("ix_dashboard_menu_items_section", "dashboard_menu_items", ["section"])
    op.create_index("ix_dashboard_menu_items_key", "dashboard_menu_items", ["key"])

    op.create_table(
        "dashboard_widgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("widget_type", sa.String(64), nullable=False),
        sa.Column("section", sa.String(100), nullable=False),
        sa.Column("data_source", sa.String(64), nullable=False, server_default="static"),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
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
        sa.UniqueConstraint("key", name="uq_dashboard_widgets_key"),
    )
    op.create_index("ix_dashboard_widgets_section", "dashboard_widgets", ["section"])
    op.create_index("ix_dashboard_widgets_key", "dashboard_widgets", ["key"])


def downgrade() -> None:
    op.drop_index("ix_dashboard_widgets_key", table_name="dashboard_widgets")
    op.drop_index("ix_dashboard_widgets_section", table_name="dashboard_widgets")
    op.drop_table("dashboard_widgets")
    op.drop_index("ix_dashboard_menu_items_key", table_name="dashboard_menu_items")
    op.drop_index("ix_dashboard_menu_items_section", table_name="dashboard_menu_items")
    op.drop_table("dashboard_menu_items")
