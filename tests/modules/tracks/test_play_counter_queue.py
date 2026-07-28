import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, cast
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yn.modules.tracks.tracks_play_counter_queue import TracksPlayCounterQueue


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
        queue.start()
        await queue.add(first)
        await queue.add(first)
        await queue.add(second)
        await asyncio.sleep(0)
        await queue.stop()

        session.execute.assert_awaited_once()
        stmt = session.execute.await_args.args[0]
        params = stmt.compile().params.values()
        assert first in params
        assert second in params
        assert 2 in params
        assert 1 in params
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

        session.execute.assert_awaited_once()
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

        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()

    asyncio.run(run())
