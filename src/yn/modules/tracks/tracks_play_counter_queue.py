import asyncio
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import case, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yn.modules.tracks.metrics_repository import (
    TrackMetricsRepository,
    utc_bucket_date,
)
from yn.modules.tracks.model import Track


@dataclass(frozen=True, slots=True)
class QualifiedPlay:
    track_id: UUID
    bucket_date: date


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
        self._queue: asyncio.Queue[QualifiedPlay | None] = asyncio.Queue()
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

    async def add(self, track_id: UUID, occurred_at: datetime | None = None) -> None:
        if not self._accepting or self._task is None or self._task.done():
            raise RuntimeError("Tracks play counter queue is not running")
        await self._queue.put(
            QualifiedPlay(
                track_id=track_id,
                bucket_date=utc_bucket_date(occurred_at),
            )
        )

    async def _process_queue(self) -> None:
        plays: list[QualifiedPlay] = []
        while True:
            try:
                play = await asyncio.wait_for(
                    self._queue.get(), timeout=self._flush_interval
                )
            except asyncio.TimeoutError:
                if plays:
                    await self._update_play_count_batch(plays)
                    plays.clear()
                continue

            if play is None:
                if plays:
                    await self._update_play_count_batch(plays)
                return

            plays.append(play)
            if len(plays) >= self._batch_size:
                await self._update_play_count_batch(plays)
                plays.clear()

    async def _update_play_count_batch(self, plays: list[QualifiedPlay]) -> None:
        total_play_counts = Counter(play.track_id for play in plays)
        daily_play_counts = Counter((play.track_id, play.bucket_date) for play in plays)
        stmt = (
            update(Track)
            .where(
                Track.id.in_(total_play_counts),
                Track.deleted_at.is_(None),
            )
            .values(
                play_count=(
                    Track.play_count + case(total_play_counts, value=Track.id, else_=0)
                )
            )
        )
        async with self._session_factory() as session:
            await session.execute(stmt)
            await TrackMetricsRepository(session).increment_qualified_plays(
                daily_play_counts
            )
            await session.commit()
