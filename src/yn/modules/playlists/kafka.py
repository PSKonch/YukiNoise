from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from faststream.kafka import KafkaRouter
from faststream.middlewares import AckPolicy
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.artists.events import ARTIST_EVENTS_TOPIC, ArtistCreatedEvent
from yn.modules.playlists.service import PlaylistService
from yn.shared.database import async_primary_session
from yn.shared.unit_of_work import UnitOfWork

PLAYLISTS_ARTIST_EVENTS_GROUP = "playlists.artist-events.v1"

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]

router = KafkaRouter()


async def create_favs_for_artist(
    event: ArtistCreatedEvent,
    session_factory: SessionFactory = async_primary_session,
) -> None:
    async with session_factory() as session:
        async with UnitOfWork(session) as uow:
            await PlaylistService(uow).create_favs_playlist(event.artist_id)


@router.subscriber(
    ARTIST_EVENTS_TOPIC,
    group_id=PLAYLISTS_ARTIST_EVENTS_GROUP,
    auto_offset_reset="earliest",
    ack_policy=AckPolicy.NACK_ON_ERROR,
    no_reply=True,
)
async def consume_artist_created(event: ArtistCreatedEvent) -> None:
    await create_favs_for_artist(event)
