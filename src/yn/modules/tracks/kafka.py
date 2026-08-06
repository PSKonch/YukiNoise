from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from faststream.kafka import KafkaRouter
from faststream.middlewares import AckPolicy
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.likes.enums import TargetType
from yn.modules.likes.events import (
    LIKES_EVENTS_TOPIC,
    LikeCreatedEvent,
    LikeDeletedEvent,
)
from yn.shared.database import async_primary_session
from yn.shared.unit_of_work import UnitOfWork

TRACKS_LIKE_EVENTS_GROUP = "tracks.like-events.v1"

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]

router = KafkaRouter()


async def sync_track_like_count(
    event: LikeCreatedEvent | LikeDeletedEvent,
    session_factory: SessionFactory = async_primary_session,
) -> None:
    if event.target_type != TargetType.TRACK:
        return

    async with session_factory() as session:
        async with UnitOfWork(session) as uow:
            await uow.tracks.sync_like_count(event.target_id)
            await uow.commit()


@router.subscriber(
    LIKES_EVENTS_TOPIC,
    group_id=TRACKS_LIKE_EVENTS_GROUP,
    auto_offset_reset="earliest",
    ack_policy=AckPolicy.NACK_ON_ERROR,
    no_reply=True,
)
async def consume_like_event(event: LikeCreatedEvent | LikeDeletedEvent) -> None:
    await sync_track_like_count(event)
