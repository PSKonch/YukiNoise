import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import Table, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yn.shared.outbox.model import OutboxEvent, OutboxMessage

logger = logging.getLogger(__name__)


class OutboxPublisher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publish: Callable[[OutboxMessage], Awaitable[None]],
        *,
        exchange: str,
        batch_size: int = 50,
        poll_interval: float = 0.5,
    ) -> None:
        self._session_factory = session_factory
        self._publish = publish
        self._exchange = exchange
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._task: asyncio.Task[None] | None = None
        self._stopping = False
        self._wake = asyncio.Event()

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stopping = False
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stopping = True
        self._wake.set()
        try:
            await self._task
        finally:
            self._task = None

    async def _run(self) -> None:
        while not self._stopping:
            published_count = 0
            try:
                published_count = await self.publish_batch()
            except Exception:
                logger.exception("Failed to publish an outbox batch")

            if self._stopping:
                return
            if published_count >= self._batch_size:
                continue

            self._wake.clear()
            try:
                await asyncio.wait_for(
                    self._wake.wait(),
                    timeout=self._poll_interval,
                )
            except asyncio.TimeoutError:
                pass

    async def publish_batch(self) -> int:
        async with self._session_factory() as session:
            async with session.begin():
                outbox_table = cast(Table, OutboxEvent.__table__)
                result = await session.execute(
                    select(outbox_table)
                    .where(
                        outbox_table.c.exchange == self._exchange,
                        outbox_table.c.published_at.is_(None),
                    )
                    .order_by(outbox_table.c.created_at.asc())
                    .limit(self._batch_size)
                    .with_for_update(skip_locked=True)
                )
                events = [
                    OutboxMessage(
                        id=row["id"],
                        event_type=row["event_type"],
                        exchange=row["exchange"],
                        routing_key=row["routing_key"],
                        payload=row["payload"],
                        occurred_at=row["occurred_at"],
                    )
                    for row in result.mappings().all()
                ]
                for event in events:
                    await self._publish(event)
                    await session.execute(
                        update(outbox_table)
                        .where(outbox_table.c.id == event.id)
                        .values(published_at=datetime.now(UTC))
                    )
                return len(events)
