"""Tracking worker — geofence evaluation loop. Same image, different command."""

from __future__ import annotations

import asyncio
import logging

from tracking.config import get_settings
from tracking.application.use_cases.process_positions import ProcessPositionsUseCase
from tracking.infrastructure.composition import build_container
from tracking.infrastructure.repositories.sql import SqlGeofenceRepository, SqlPositionRepository

logger = logging.getLogger("tracking.worker")


async def run() -> None:
    settings = get_settings()
    container = build_container(settings)
    logger.info("tracking-worker started mode=%s", settings.deployment_mode)
    try:
        while True:
            async with container.session_factory() as session:
                use_case = ProcessPositionsUseCase(
                    positions=SqlPositionRepository(session),
                    geofences=SqlGeofenceRepository(session),
                    events=container.event_bus,
                )
                processed = await use_case.execute()
                await session.commit()
                if processed:
                    logger.info("processed %s positions", processed)
            await asyncio.sleep(settings.worker_poll_seconds)
    finally:
        if container.hub is not None:
            await container.hub.aclose()
        await container.engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
