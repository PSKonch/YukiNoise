import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta, timezone
from typing import AsyncIterator, cast
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yn.modules.tracks.tracks_play_counter_queue import TracksPlayCounterQueue

POSTGRES_DIALECT = cast(Callable[[], Dialect], PGDialect)()


def test_flushes_full_batch_and_aggregates_duplicate_tracks() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)

        @asynccontextmanager
        async def session_factory() -> AsyncIterator[AsyncSession]:
            yield session

        queue = TracksPlayCounterQueue(
            cast(async_sessionmaker[AsyncSession], session_factory),
            batch_size=3,
            flush_interval=60,
        )
        first, second = uuid4(), uuid4()
        occurred_at = datetime(2026, 8, 7, 12, tzinfo=UTC)
        queue.start()
        await queue.add(first, occurred_at)
        await queue.add(first, occurred_at)
        await queue.add(second, occurred_at)
        await asyncio.sleep(0)
        await queue.stop()

        assert session.execute.await_count == 2
        total_stmt = session.execute.await_args_list[0].args[0]
        total_params = total_stmt.compile().params.values()
        assert first in total_params
        assert second in total_params
        assert 2 in total_params
        assert 1 in total_params

        daily_stmt = session.execute.await_args_list[1].args[0]
        compiled = daily_stmt.compile(dialect=POSTGRES_DIALECT)
        sql = str(compiled)
        assert "INSERT INTO track_metrics_daily" in sql
        assert "ON CONFLICT (track_id, bucket_date) DO UPDATE" in sql
        assert "track_metrics_daily.qualified_plays + excluded.qualified_plays" in sql
        assert occurred_at.date() in compiled.params.values()
        assert 2 in compiled.params.values()
        assert 1 in compiled.params.values()
        assert None not in compiled.params.values()
        session.commit.assert_awaited_once()

    asyncio.run(run())


def test_stop_flushes_partial_batch() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)

        @asynccontextmanager
        async def session_factory() -> AsyncIterator[AsyncSession]:
            yield session

        queue = TracksPlayCounterQueue(
            cast(async_sessionmaker[AsyncSession], session_factory),
            batch_size=10,
            flush_interval=60,
        )
        queue.start()
        await queue.add(uuid4())
        await queue.stop()

        assert session.execute.await_count == 2
        session.commit.assert_awaited_once()

    asyncio.run(run())


def test_flushes_partial_batch_after_interval() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        flushed = asyncio.Event()

        async def commit() -> None:
            flushed.set()

        session.commit.side_effect = commit

        @asynccontextmanager
        async def session_factory() -> AsyncIterator[AsyncSession]:
            yield session

        queue = TracksPlayCounterQueue(
            cast(async_sessionmaker[AsyncSession], session_factory),
            batch_size=10,
            flush_interval=0.01,
        )
        queue.start()
        await queue.add(uuid4())
        await asyncio.wait_for(flushed.wait(), timeout=1)
        await queue.stop()

        assert session.execute.await_count == 2
        session.commit.assert_awaited_once()

    asyncio.run(run())


def test_uses_the_utc_day_when_a_play_is_queued() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)

        @asynccontextmanager
        async def session_factory() -> AsyncIterator[AsyncSession]:
            yield session

        queue = TracksPlayCounterQueue(
            cast(async_sessionmaker[AsyncSession], session_factory),
            batch_size=1,
            flush_interval=60,
        )
        moscow_time = datetime(
            2026,
            8,
            8,
            1,
            30,
            tzinfo=timezone(timedelta(hours=3)),
        )
        queue.start()
        await queue.add(uuid4(), moscow_time)
        await asyncio.sleep(0)
        await queue.stop()

        daily_stmt = session.execute.await_args_list[1].args[0]
        compiled = daily_stmt.compile(dialect=POSTGRES_DIALECT)
        assert datetime(2026, 8, 7, tzinfo=UTC).date() in compiled.params.values()
        assert None not in compiled.params.values()

    asyncio.run(run())
