import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from uuid import UUID

from faststream.kafka import KafkaBroker
from sqlalchemy.ext.asyncio import AsyncSession

from yn.shared.database import async_primary_session
from yn.shared.outbox.model import OutboxModel
from yn.shared.outbox.repository import OutboxRepository
from yn.shared.publisher import KafkaPublisher, kafka_broker
from yn.shared.settings import settings

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class OutboxPublisher:
    def __init__(
        self,
        session_factory: SessionFactory,
        broker: KafkaBroker,
        *,
        batch_size: int = 50,
        poll_interval: float = 0.5,
        retry_base_seconds: float = 1.0,
        retry_max_seconds: float = 300.0,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("Outbox batch size must be positive")
        if poll_interval <= 0:
            raise ValueError("Outbox poll interval must be positive")
        if retry_base_seconds <= 0:
            raise ValueError("Outbox retry base must be positive")
        if retry_max_seconds < retry_base_seconds:
            raise ValueError("Outbox retry maximum must not be less than its base")

        self._session_factory = session_factory
        self._broker = broker
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._retry_base_seconds = retry_base_seconds
        self._retry_max_seconds = retry_max_seconds
        self._task: asyncio.Task[None] | None = None
        self._stopping = False
        self._wake = asyncio.Event()

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stopping = False
        self._task = asyncio.create_task(self._run(), name="outbox-publisher")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stopping = True
        self._wake.set()
        try:
            await self._task
        finally:
            self._task = None

    async def publish_now(self, event_id: UUID) -> bool:
        """Best-effort immediate delivery; failed events stay available for retry."""
        try:
            published = await self._publish_one(
                event_id,
                ignore_retry_schedule=True,
            )
        except Exception:
            logger.exception("Failed to process outbox event %s immediately", event_id)
            published = False
        if not published:
            self._wake.set()
        return published

    async def publish_batch(self) -> int:
        async with self._session_factory() as session:
            repository = OutboxRepository(session)
            event_ids = await repository.get_pending_ids(limit=self._batch_size)

        if not event_ids:
            return 0

        results = await asyncio.gather(
            *(self._publish_one(event_id) for event_id in event_ids),
            return_exceptions=True,
        )
        published_count = 0
        for event_id, result in zip(event_ids, results, strict=True):
            if isinstance(result, BaseException):
                logger.error(
                    "Failed to process outbox event %s",
                    event_id,
                    exc_info=(type(result), result, result.__traceback__),
                )
            elif result:
                published_count += 1
        return published_count

    async def _run(self) -> None:
        while not self._stopping:
            processed_count = 0
            try:
                processed_count = await self.publish_batch()
            except Exception:
                logger.exception("Failed to process an outbox batch")

            if self._stopping:
                return
            if processed_count >= self._batch_size:
                continue

            self._wake.clear()
            try:
                await asyncio.wait_for(
                    self._wake.wait(),
                    timeout=self._poll_interval,
                )
            except TimeoutError:
                pass

    async def _publish_one(
        self,
        event_id: UUID,
        *,
        ignore_retry_schedule: bool = False,
    ) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                repository = OutboxRepository(session)
                event = await repository.lock_pending(
                    event_id,
                    ignore_retry_schedule=ignore_retry_schedule,
                )
                if event is None:
                    return False

                try:
                    await self._publish_event(event)
                except Exception:
                    repository.mark_failed(
                        event,
                        next_attempt_at=self._next_attempt_at(event.attempts),
                    )
                    logger.exception(
                        "Failed to publish outbox event %s to %s",
                        event.id,
                        event.topic,
                    )
                    return False

                repository.mark_published(event)
                return True

    async def _publish_event(self, event: OutboxModel) -> None:
        publisher = KafkaPublisher(event.topic, broker=self._broker)
        await publisher.publish(
            message=event.payload,
            key=event.message_key,
            headers={
                "event-type": event.event_type,
                "event-version": str(event.version),
            },
            correlation_id=str(event.id),
        )

    def _next_attempt_at(self, attempts: int) -> datetime:
        delay = min(
            self._retry_base_seconds * (2**attempts),
            self._retry_max_seconds,
        )
        return datetime.now(UTC) + timedelta(seconds=delay)


outbox_publisher = OutboxPublisher(
    async_primary_session,
    kafka_broker,
    batch_size=settings.outbox_batch_size,
    poll_interval=settings.outbox_poll_interval_seconds,
    retry_base_seconds=settings.outbox_retry_base_seconds,
    retry_max_seconds=settings.outbox_retry_max_seconds,
)


def get_outbox_publisher() -> OutboxPublisher:
    return outbox_publisher
