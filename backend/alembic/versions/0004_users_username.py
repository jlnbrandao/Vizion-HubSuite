"""Add unique username column to users."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_users_username"
down_revision: str | None = "0003_permission_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("username", sa.String(32), nullable=True),
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, email FROM users")).mappings().all()
    used: set[str] = set()
    for row in rows:
        local = str(row["email"]).split("@", 1)[0].lower()
        cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in local)
        cleaned = cleaned.strip("_") or "user"
        if cleaned[0].isdigit():
            cleaned = f"u_{cleaned}"
        base = cleaned[:32]
        if len(base) < 3:
            base = (base + "user")[:32]
        candidate = base
        suffix = 1
        while candidate in used:
            tail = f"_{suffix}"
            candidate = f"{base[: 32 - len(tail)]}{tail}"
            suffix += 1
        used.add(candidate)
        conn.execute(
            sa.text("UPDATE users SET username = :username WHERE id = :id"),
            {"username": candidate, "id": row["id"]},
        )

    op.alter_column("users", "username", nullable=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_index("ix_users_username", "users", ["username"])


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "username")
