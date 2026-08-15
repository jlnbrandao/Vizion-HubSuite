"""Audit retention job — delete events older than the retention window.

Runs across every tenant, so it bypasses RLS. Meant for cron / pg_cron:

    python -m scripts.prune_audit            # AUDIT_RETENTION_DAYS
    python -m scripts.prune_audit --days 90
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from src.config.settings import get_settings
from src.shared.infrastructure.di.container import create_container
from src.shared.infrastructure.tenant_context import bind_rls_bypass, unbind_rls_bypass

logger = logging.getLogger("prune_audit")


async def prune(retention_days: int) -> int:
    container = create_container()
    audit = container.audit_service()
    token = bind_rls_bypass(True)
    try:
        async with container.unit_of_work() as uow:
            removed = await audit.prune(retention_days=retention_days)
            await uow.commit()
    finally:
        unbind_rls_bypass(token)
        await container.engine().dispose()
        await container.redis().aclose()
    return removed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Prune old audit events")
    parser.add_argument(
        "--days",
        type=int,
        default=settings.audit_retention_days,
        help="retention window in days (default: AUDIT_RETENTION_DAYS)",
    )
    args = parser.parse_args()

    removed = asyncio.run(prune(args.days))
    logger.info("Pruned %s audit events older than %s days", removed, args.days)


if __name__ == "__main__":
    main()
