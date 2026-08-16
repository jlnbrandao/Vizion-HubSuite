"""Seed a standalone demo tenant. Never contacts Platform Core."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID, uuid4

from sqlalchemy import select

from tracking.config import get_settings
from tracking.infrastructure.composition import build_container
from tracking.infrastructure.database.models import TenantEntitlementModel, TenantModel, UserModel
from tracking.infrastructure.security.passwords import hash_password
from tracking.permissions import CAPABILITY_ADVANCED_TELEMETRY, CAPABILITY_BASIC

logger = logging.getLogger("tracking.seed")

DEMO_TENANT_ID = UUID("b0000000-0000-4000-8000-000000000001")
DEMO_USER_ID = UUID("b0000000-0000-4000-8000-000000000011")


async def seed() -> None:
    settings = get_settings()
    if settings.app_env != "development" and not settings.seed_allow_insecure:
        raise SystemExit("Refusing to seed outside development (set SEED_ALLOW_INSECURE=true)")
    container = build_container(settings)
    async with container.session_factory() as session:
        existing = await session.execute(select(TenantModel).where(TenantModel.slug == "demo"))
        if existing.scalar_one_or_none() is None:
            session.add(TenantModel(id=DEMO_TENANT_ID, slug="demo", name="Demo", is_active=True))
            session.add(
                UserModel(
                    id=DEMO_USER_ID,
                    tenant_id=DEMO_TENANT_ID,
                    email="admin@demo.local",
                    full_name="Tracking Admin",
                    hashed_password=hash_password("admin123"),
                    role_name="ADMIN",
                    is_active=True,
                )
            )
            session.add(
                TenantEntitlementModel(
                    id=uuid4(), tenant_id=DEMO_TENANT_ID, capability=CAPABILITY_BASIC
                )
            )
            session.add(
                TenantEntitlementModel(
                    id=uuid4(),
                    tenant_id=DEMO_TENANT_ID,
                    capability=CAPABILITY_ADVANCED_TELEMETRY,
                )
            )
            await session.commit()
            logger.info("seeded demo tenant admin@demo.local / admin123")
        else:
            logger.info("demo tenant already present")
    await container.engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())


if __name__ == "__main__":
    main()
