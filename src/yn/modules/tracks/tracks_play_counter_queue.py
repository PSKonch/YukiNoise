import asyncio
from collections import Counter
from uuid import UUID

from sqlalchemy import case, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yn.modules.tracks.model import Track


class TracksPlayCounterQueue:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        batch_size: int = 10,
        flush_interval: float = 1.0,
    ) -> None:
        self._session_factory = session_factory
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._queue: asyncio.Queue[UUID | None] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._accepting = False

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._accepting = True
        self._task = asyncio.create_task(self._process_queue())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._accepting = False
        await self._queue.put(None)
        try:
            await self._task
        finally:
            self._task = None

    async def add(self, track_id: UUID) -> None:
        if not self._accepting or self._task is None or self._task.done():
            raise RuntimeError("Tracks play counter queue is not running")
        await self._queue.put(track_id)

    async def _process_queue(self) -> None:
        track_ids: list[UUID] = []
        while True:
            try:
                track_id = await asyncio.wait_for(
                    self._queue.get(), timeout=self._flush_interval
                )
            except asyncio.TimeoutError:
                if track_ids:
                    await self._update_play_count_batch(track_ids)
                    track_ids.clear()
                continue

            if track_id is None:
                if track_ids:
                    await self._update_play_count_batch(track_ids)
                return

            track_ids.append(track_id)
            if len(track_ids) >= self._batch_size:
                await self._update_play_count_batch(track_ids)
                track_ids.clear()

    async def _update_play_count_batch(self, track_ids: list[UUID]) -> None:
        play_counts = Counter(track_ids)
        stmt = (
            update(Track)
            .where(
                Track.id.in_(play_counts),
                Track.deleted_at.is_(None),
            )
            .values(
                play_count=Track.play_count + case(play_counts, value=Track.id, else_=0)
            )
        )
        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()
