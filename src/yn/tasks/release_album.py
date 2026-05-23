from yn.shared.database import async_session
from yn.shared.unit_of_work import UnitOfWork
from yn.tasks.broker import broker


@broker.task(schedule=[{"interval": 60}])
async def release_due_albums() -> None:
    async with async_session() as session:
        async with UnitOfWork(session) as uow:
            due_albums = await uow.albums.get_scheduled_albums_due_for_release()
            for album in due_albums:
                await uow.albums.release_album(album.id)
