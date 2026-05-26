import logging

from yn.shared.database import async_session
from yn.shared.unit_of_work import UnitOfWork
from yn.tasks.broker import broker

logger = logging.getLogger(__name__)


@broker.task(schedule=[{"interval": 60}])
async def release_due_releases() -> None:
    async with async_session() as session:
        async with UnitOfWork(session) as uow:
            due_releases = await uow.releases.get_scheduled_releases_due_for_release()
            for release in due_releases:
                try:
                    updated_release = await uow.releases.release_release(release.id)
                    if updated_release is None:
                        logger.warning(
                            "Scheduled release is not eligible for publish",
                            extra={"release_id": str(release.id)},
                        )
                        continue
                    await uow.commit()
                except Exception:
                    await uow.rollback()
                    logger.exception(
                        "Failed to publish scheduled release",
                        extra={"release_id": str(release.id)},
                    )
