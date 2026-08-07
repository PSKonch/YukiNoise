import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, AsyncIterator, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from faststream.middlewares import AckPolicy
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.auth import model as _auth_model  # noqa: F401
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
def test_track_like_event_recalculates_total_and_updates_daily_metrics(
    event_class: type[LikeCreatedEvent] | type[LikeDeletedEvent],
) -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)

        @asynccontextmanager
        async def session_factory() -> AsyncIterator[AsyncSession]:
            yield session

        track_id = uuid4()
        event_id = uuid4()
        event = event_class(
            event_id=event_id,
            like_id=uuid4(),
            artist_id=uuid4(),
            target_type=TargetType.TRACK,
            target_id=track_id,
            occurred_at=datetime(
                2026,
                8,
                8,
                1,
                30,
                tzinfo=timezone(timedelta(hours=3)),
            ),
        )
        session.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: track_id),
            SimpleNamespace(scalar_one_or_none=lambda: event_id),
            SimpleNamespace(),
        ]

        await sync_track_like_count(event, cast(SessionFactory, session_factory))

        assert session.execute.await_count == 3

        total_statement = session.execute.await_args_list[0].args[0]
        total_sql = str(total_statement.compile(dialect=POSTGRES_DIALECT))
        assert "UPDATE tracks SET like_count=(SELECT count(likes.id)" in total_sql
        assert "likes.target_type" in total_sql
        assert "likes.target_id" in total_sql

        receipt_statement = session.execute.await_args_list[1].args[0]
        receipt_sql = str(receipt_statement.compile(dialect=POSTGRES_DIALECT))
        assert "INSERT INTO metric_event_receipts" in receipt_sql
        assert "ON CONFLICT (consumer, event_id) DO NOTHING" in receipt_sql
        assert (
            event_id
            in receipt_statement.compile(dialect=POSTGRES_DIALECT).params.values()
        )

        metrics_statement = session.execute.await_args_list[2].args[0]
        metrics_compiled = metrics_statement.compile(dialect=POSTGRES_DIALECT)
        metrics_sql = str(metrics_compiled)
        metric_name = (
            "likes_added" if event_class is LikeCreatedEvent else "likes_removed"
        )
        assert "INSERT INTO track_metrics_daily" in metrics_sql
        assert (
            f"track_metrics_daily.{metric_name} + excluded.{metric_name}" in metrics_sql
        )
        assert datetime(2026, 8, 7, tzinfo=UTC).date() in (
            metrics_compiled.params.values()
        )
        assert None not in metrics_compiled.params.values()
        session.commit.assert_awaited_once()

    asyncio.run(run())


def test_duplicate_like_event_does_not_increment_daily_metrics() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)

        @asynccontextmanager
        async def session_factory() -> AsyncIterator[AsyncSession]:
            yield session

        track_id = uuid4()
        event = LikeCreatedEvent(
            like_id=uuid4(),
            artist_id=uuid4(),
            target_type=TargetType.TRACK,
            target_id=track_id,
        )
        session.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: track_id),
            SimpleNamespace(scalar_one_or_none=lambda: None),
        ]

        await sync_track_like_count(event, cast(SessionFactory, session_factory))

        assert session.execute.await_count == 2
        sql_statements = [
            str(call.args[0].compile(dialect=POSTGRES_DIALECT))
            for call in session.execute.await_args_list
        ]
        assert not any("track_metrics_daily" in sql for sql in sql_statements)
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
