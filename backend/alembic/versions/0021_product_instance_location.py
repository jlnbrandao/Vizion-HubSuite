"""Deployment location fields on product_instances."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_product_instance_location"
down_revision: str | None = "0020_product_instances"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_instances",
        sa.Column("environment", sa.String(32), nullable=False, server_default="local_docker"),
    )
    op.add_column(
        "product_instances",
        sa.Column("host", sa.String(255), nullable=False, server_default=""),
    )
    op.add_column(
        "product_instances",
        sa.Column("api_port", sa.Integer(), nullable=True),
    )
    op.add_column(
        "product_instances",
        sa.Column("ui_host", sa.String(255), nullable=True),
    )
    op.add_column(
        "product_instances",
        sa.Column("ui_port", sa.Integer(), nullable=True),
    )
    op.add_column(
        "product_instances",
        sa.Column("scheme", sa.String(8), nullable=False, server_default="http"),
    )
    op.add_column(
        "product_instances",
        sa.Column("notes", sa.String(500), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("product_instances", "notes")
    op.drop_column("product_instances", "scheme")
    op.drop_column("product_instances", "ui_port")
    op.drop_column("product_instances", "ui_host")
    op.drop_column("product_instances", "api_port")
    op.drop_column("product_instances", "host")
    op.drop_column("product_instances", "environment")
