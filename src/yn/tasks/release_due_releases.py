import logging

from yn.shared.database import async_session
from yn.shared.unit_of_work import UnitOfWork
from yn.tasks.broker import broker

logger = logging.getLogger(__name__)


@broker.task(schedule=[{"interval": 60}])
async def release_due_releases() -> None:
    async with async_session() as session:
        try:
            async with UnitOfWork(session) as uow:
                released_ids = await uow.releases.publish_due_releases()
                if not released_ids:
                    return
            logger.info(
                "Published scheduled releases",
                extra={"release_ids": [str(release_id) for release_id in released_ids]},
            )
        except Exception:
            logger.exception("Failed to publish scheduled releases")
