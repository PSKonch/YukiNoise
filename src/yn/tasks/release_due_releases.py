from yn.shared.database import async_session
from yn.shared.unit_of_work import UnitOfWork
from yn.tasks.broker import broker


@broker.task(schedule=[{"interval": 60}])
async def release_due_releases() -> None:
    async with async_session() as session:
        async with UnitOfWork(session) as uow:
            due_releases = await uow.releases.get_scheduled_releases_due_for_release()
            for release in due_releases:
                await uow.releases.release(release.id)
