import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, AsyncIterator, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from faststream.middlewares import AckPolicy
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.likes.enums import TargetType
from yn.modules.likes.events import (
    LIKES_EVENTS_TOPIC,
    LikeCreatedEvent,
    LikeDeletedEvent,
)
from yn.modules.tracks.kafka import (
    TRACKS_LIKE_EVENTS_GROUP,
    SessionFactory,
    router,
    sync_track_like_count,
)

POSTGRES_DIALECT = cast(Callable[[], Dialect], PGDialect)()


def test_consumer_uses_dedicated_group_and_at_least_once_acknowledgement() -> None:
    subscriber = cast(Any, router.subscribers[0])

    assert subscriber.topics == [LIKES_EVENTS_TOPIC]
    assert subscriber.group_id == TRACKS_LIKE_EVENTS_GROUP
    assert subscriber.ack_policy is AckPolicy.NACK_ON_ERROR


@pytest.mark.parametrize("event_class", [LikeCreatedEvent, LikeDeletedEvent])
def test_track_like_event_recalculates_counter_idempotently(
    event_class: type[LikeCreatedEvent] | type[LikeDeletedEvent],
) -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = SimpleNamespace(
            scalar_one_or_none=lambda: uuid4()
        )

        @asynccontextmanager
        async def session_factory() -> AsyncIterator[AsyncSession]:
            yield session

        track_id = uuid4()
        event = event_class(
            like_id=uuid4(),
            artist_id=uuid4(),
            target_type=TargetType.TRACK,
            target_id=track_id,
        )

        await sync_track_like_count(event, cast(SessionFactory, session_factory))

        session.execute.assert_awaited_once()
        statement = session.execute.await_args.args[0]
        sql = str(statement.compile(dialect=POSTGRES_DIALECT))
        assert "UPDATE tracks SET like_count=(SELECT count(likes.id)" in sql
        assert "likes.target_type" in sql
        assert "likes.target_id" in sql
        assert track_id in statement.compile(dialect=POSTGRES_DIALECT).params.values()
        session.commit.assert_awaited_once()

    asyncio.run(run())


def test_consumer_ignores_non_track_like_events() -> None:
    async def run() -> None:
        session_factory = AsyncMock()
        event = LikeCreatedEvent(
            like_id=uuid4(),
            artist_id=uuid4(),
            target_type=TargetType.PLAYLIST,
            target_id=uuid4(),
        )

        await sync_track_like_count(
            event,
            cast(SessionFactory, session_factory),
        )

        session_factory.assert_not_called()

    asyncio.run(run())
