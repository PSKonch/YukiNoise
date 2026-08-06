import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, cast
from unittest.mock import AsyncMock
from uuid import uuid4

from faststream.middlewares import AckPolicy
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.artists.events import ARTIST_EVENTS_TOPIC, ArtistCreatedEvent
from yn.modules.playlists.kafka import (
    PLAYLISTS_ARTIST_EVENTS_GROUP,
    SessionFactory,
    create_favs_for_artist,
    router,
)


def test_consumer_uses_dedicated_group_and_at_least_once_acknowledgement() -> None:
    subscriber = next(
        cast(Any, item)
        for item in router.subscribers
        if cast(Any, item).group_id == PLAYLISTS_ARTIST_EVENTS_GROUP
    )

    assert subscriber.topics == [ARTIST_EVENTS_TOPIC]
    assert subscriber.group_id == PLAYLISTS_ARTIST_EVENTS_GROUP
    assert subscriber.ack_policy is AckPolicy.NACK_ON_ERROR


def test_artist_created_event_creates_system_favs_idempotently() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)

        @asynccontextmanager
        async def session_factory() -> AsyncIterator[AsyncSession]:
            yield session

        event = ArtistCreatedEvent(
            artist_id=uuid4(),
            user_id=uuid4(),
            displayed_name="Artist",
        )

        await create_favs_for_artist(
            event,
            cast(SessionFactory, session_factory),
        )

        session.execute.assert_awaited_once()
        statement = session.execute.await_args.args[0]
        compiled = statement.compile()
        assert "ON CONFLICT" in str(compiled)
        assert event.artist_id in compiled.params.values()
        assert "favs" in compiled.params.values()
        session.commit.assert_awaited_once()

    asyncio.run(run())
