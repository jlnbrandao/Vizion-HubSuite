"""Register GIS as a sellable distributable product."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022_gis_service"
down_revision: str | None = "0021_product_instance_location"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO services (
                id, slug, namespace, name, description, is_core, tenant_only, is_active
            )
            VALUES (
                gen_random_uuid(),
                'gis',
                'gis',
                'GIS',
                'GIS product — maps and geospatial workspace',
                false,
                true,
                true
            )
            ON CONFLICT (slug) DO UPDATE
            SET namespace = EXCLUDED.namespace,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                tenant_only = true
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM services WHERE slug = 'gis'"))
