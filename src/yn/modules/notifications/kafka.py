from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from faststream.kafka import KafkaRouter
from faststream.middlewares import AckPolicy
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.releases.events import RELEASE_EVENTS_TOPIC, ReleasePublishedEvent
from yn.shared.database import async_primary_session
from yn.shared.unit_of_work import UnitOfWork

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]
NOTIFICATIONS_RELEASE_EVENTS_GROUP = "notifications.release-events.v1"
router = KafkaRouter()


async def notify_release_followers(
    event: ReleasePublishedEvent,
    session_factory: SessionFactory = async_primary_session,
    *,
    batch_size: int = 100,
) -> None:
    if batch_size < 1:
        raise ValueError("Notification batch size must be positive")
    after = None
    while True:
        # Commit each bounded batch. If a later batch fails, Kafka redelivers the
        # event and the unique user/release constraint skips existing messages.
        async with session_factory() as session:
            async with UnitOfWork(session) as uow:
                source = await uow.notifications.get_release_source(event.release_id)
                if source is None:
                    return
                recipients = await uow.notifications.get_recipient_ids(
                    source.artist_id,
                    occurred_at=event.occurred_at,
                    after=after,
                    limit=batch_size,
                )
                if not recipients:
                    return
                await uow.notifications.add_release_notifications(
                    source,
                    recipients,
                    occurred_at=event.occurred_at,
                )
                await uow.commit()
        after = recipients[-1]
        if len(recipients) < batch_size:
            return


@router.subscriber(
    RELEASE_EVENTS_TOPIC,
    group_id=NOTIFICATIONS_RELEASE_EVENTS_GROUP,
    auto_offset_reset="earliest",
    ack_policy=AckPolicy.NACK_ON_ERROR,
    no_reply=True,
)
async def consume_release_published(event: ReleasePublishedEvent) -> None:
    await notify_release_followers(event)
