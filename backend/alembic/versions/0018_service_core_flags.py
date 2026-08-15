"""Only iam and platform are core; the Integration Hub is a sellable service.

Migration 0016 marked every shipped service as core, which made `integration`
impossible to suspend per tenant — the opposite of what entitlements are for.
`is_core` now means "the Hub cannot run without it".
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_service_core_flags"
down_revision: str | None = "0017_usage_metering"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SLUGS = ("iam", "platform")


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE services SET is_core = (slug = ANY(:core))"
        ).bindparams(sa.bindparam("core", value=list(CORE_SLUGS), type_=sa.ARRAY(sa.String)))
    )


def downgrade() -> None:
    op.execute(sa.text("UPDATE services SET is_core = true"))
