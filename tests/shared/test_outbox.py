import asyncio
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from faststream.kafka import KafkaBroker
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.artists import model as _artists_model  # noqa: F401
from yn.modules.auth import model as _auth_model  # noqa: F401
from yn.modules.commentaries import model as _commentaries_model  # noqa: F401
from yn.modules.follows import model as _follows_model  # noqa: F401
from yn.modules.likes import model as _likes_model  # noqa: F401
from yn.modules.notifications import model as _notifications_model  # noqa: F401
from yn.modules.playlists import model as _playlists_model  # noqa: F401
from yn.modules.posts import model as _posts_model  # noqa: F401
from yn.modules.releases import model as _releases_model  # noqa: F401
from yn.modules.tracks import model as _tracks_model  # noqa: F401
from yn.modules.users import model as _users_model  # noqa: F401
from yn.shared.outbox.model import OutboxModel
from yn.shared.outbox.publisher import OutboxPublisher, SessionFactory
from yn.shared.outbox.repository import OutboxRepository


class TransactionContext:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        return None


class SessionContext(AbstractAsyncContextManager[AsyncSession]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        return None


def make_event() -> OutboxModel:
    return OutboxModel(
        id=uuid4(),
        topic="artists.events",
        message_key=str(uuid4()),
        event_type="artist.created",
        version=1,
        payload={"artist_id": str(uuid4())},
        attempts=0,
    )


def make_publisher(
    session: AsyncSession,
    broker: KafkaBroker,
) -> OutboxPublisher:
    session_factory = cast(SessionFactory, lambda: SessionContext(session))
    return OutboxPublisher(session_factory, broker)


def test_repository_adds_event_to_current_transaction() -> None:
    async def run() -> None:
        session = MagicMock(spec=AsyncSession)
        event_id = uuid4()
        repository = OutboxRepository(cast(AsyncSession, session))

        event = await repository.add(
            event_id=event_id,
            topic="artists.events",
            message_key="artist-1",
            event_type="artist.created",
            version=1,
            payload={"artist_id": "artist-1"},
        )

        assert event.id == event_id
        assert event.topic == "artists.events"
        assert event.message_key == "artist-1"
        session.add.assert_called_once_with(event)
        session.commit.assert_not_called()

    asyncio.run(run())


def test_immediate_publish_marks_event_as_published() -> None:
    async def run() -> None:
        event = make_event()
        session = AsyncMock(spec=AsyncSession)
        session.begin = MagicMock(return_value=TransactionContext())
        result = MagicMock()
        result.scalar_one_or_none.return_value = event
        session.execute.return_value = result
        broker = AsyncMock(spec=KafkaBroker)
        publisher = make_publisher(session, cast(KafkaBroker, broker))

        assert await publisher.publish_now(event.id) is True
        assert event.message_key is not None

        broker.publish.assert_awaited_once_with(
            event.payload,
            topic=event.topic,
            key=event.message_key.encode(),
            partition=None,
            timestamp_ms=None,
            headers={
                "event-type": event.event_type,
                "event-version": str(event.version),
            },
            correlation_id=str(event.id),
            no_confirm=False,
        )
        assert event.published_at is not None
        assert event.next_attempt_at is None

    asyncio.run(run())


def test_failed_immediate_publish_schedules_retry() -> None:
    async def run() -> None:
        event = make_event()
        session = AsyncMock(spec=AsyncSession)
        session.begin = MagicMock(return_value=TransactionContext())
        result = MagicMock()
        result.scalar_one_or_none.return_value = event
        session.execute.return_value = result
        broker = AsyncMock(spec=KafkaBroker)
        broker.publish.side_effect = RuntimeError("Kafka unavailable")
        publisher = make_publisher(session, cast(KafkaBroker, broker))
        started_at = datetime.now(UTC)

        assert await publisher.publish_now(event.id) is False

        assert event.published_at is None
        assert event.attempts == 1
        assert event.next_attempt_at is not None
        assert event.next_attempt_at > started_at

    asyncio.run(run())


def test_locked_or_already_published_event_is_not_sent_twice() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        session.begin = MagicMock(return_value=TransactionContext())
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result
        broker = AsyncMock(spec=KafkaBroker)
        publisher = make_publisher(session, cast(KafkaBroker, broker))

        assert await publisher.publish_now(uuid4()) is False
        broker.publish.assert_not_awaited()

    asyncio.run(run())


def test_immediate_database_failure_is_left_for_background_retry() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        session.begin = MagicMock(return_value=TransactionContext())
        session.execute.side_effect = RuntimeError("PostgreSQL unavailable")
        broker = AsyncMock(spec=KafkaBroker)
        publisher = make_publisher(session, cast(KafkaBroker, broker))

        assert await publisher.publish_now(uuid4()) is False
        broker.publish.assert_not_awaited()

    asyncio.run(run())
