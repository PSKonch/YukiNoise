import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, AsyncIterator, cast
from unittest.mock import AsyncMock
from uuid import uuid4

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
from yn.modules.playlists.kafka import (
    PLAYLISTS_LIKE_EVENTS_GROUP,
    SessionFactory,
    router,
    sync_favs_for_track_like,
)

POSTGRES_DIALECT = cast(Callable[[], Dialect], PGDialect)()


def test_consumer_uses_dedicated_group_and_at_least_once_acknowledgement() -> None:
    subscriber = next(
        cast(Any, item)
        for item in router.subscribers
        if cast(Any, item).group_id == PLAYLISTS_LIKE_EVENTS_GROUP
    )

    assert subscriber.topics == [LIKES_EVENTS_TOPIC]
    assert subscriber.ack_policy is AckPolicy.NACK_ON_ERROR


def test_track_like_created_adds_track_to_system_favs_idempotently() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = SimpleNamespace()

        @asynccontextmanager
        async def session_factory() -> AsyncIterator[AsyncSession]:
            yield session

        artist_id = uuid4()
        track_id = uuid4()
        event = LikeCreatedEvent(
            like_id=uuid4(),
            artist_id=artist_id,
            target_type=TargetType.TRACK,
            target_id=track_id,
        )

        await sync_favs_for_track_like(event, cast(SessionFactory, session_factory))

        assert session.execute.await_count == 2
        create_favs = session.execute.await_args_list[0].args[0]
        add_track = session.execute.await_args_list[1].args[0]
        create_sql = str(create_favs.compile(dialect=POSTGRES_DIALECT))
        add_sql = str(add_track.compile(dialect=POSTGRES_DIALECT))
        assert "INSERT INTO playlists" in create_sql
        assert "ON CONFLICT" in create_sql
        assert "INSERT INTO playlist_tracks" in add_sql
        assert "ON CONFLICT" in add_sql
        add_params = add_track.compile(dialect=POSTGRES_DIALECT).params.values()
        assert artist_id in add_params
        assert track_id in add_params
        session.commit.assert_awaited_once()

    asyncio.run(run())


def test_track_like_deleted_removes_track_from_system_favs_idempotently() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = SimpleNamespace()

        @asynccontextmanager
        async def session_factory() -> AsyncIterator[AsyncSession]:
            yield session

        artist_id = uuid4()
        track_id = uuid4()
        event = LikeDeletedEvent(
            like_id=uuid4(),
            artist_id=artist_id,
            target_type=TargetType.TRACK,
            target_id=track_id,
        )

        await sync_favs_for_track_like(event, cast(SessionFactory, session_factory))

        session.execute.assert_awaited_once()
        remove_track = session.execute.await_args.args[0]
        remove_sql = str(remove_track.compile(dialect=POSTGRES_DIALECT))
        assert "DELETE FROM playlist_tracks" in remove_sql
        remove_params = remove_track.compile(dialect=POSTGRES_DIALECT).params.values()
        assert artist_id in remove_params
        assert track_id in remove_params
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

        await sync_favs_for_track_like(
            event,
            cast(SessionFactory, session_factory),
        )

        session_factory.assert_not_called()

    asyncio.run(run())
