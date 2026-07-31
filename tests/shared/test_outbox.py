import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yn.shared.outbox.model import OutboxMessage
from yn.shared.outbox.publisher import OutboxPublisher
from yn.shared.outbox.repository import OutboxRepository

POSTGRES_DIALECT = cast(Callable[[], Dialect], PGDialect)()


class TransactionContext:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        return None


class SessionContext:
    def __init__(self, session: Any) -> None:
        self.session = session

    async def __aenter__(self) -> Any:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        return None


def make_event() -> OutboxMessage:
    return OutboxMessage(
        id=uuid4(),
        event_type="artist.created",
        exchange="artists.events",
        routing_key="artist.created.v1",
        payload={"artist_id": str(uuid4())},
        occurred_at=datetime.now(UTC),
    )


def test_repository_adds_event_to_current_transaction() -> None:
    async def run() -> None:
        session = MagicMock(spec=AsyncSession)

        async def execute(statement: Any) -> None:
            session.statement = statement

        session.execute.side_effect = execute
        event = make_event()

        await OutboxRepository(session).add(
            event_id=event.id,
            event_type=event.event_type,
            exchange=event.exchange,
            routing_key=event.routing_key,
            payload=event.payload,
            occurred_at=event.occurred_at,
        )

        statement = session.statement
        compiled = statement.compile(dialect=POSTGRES_DIALECT)
        assert event.id in compiled.params.values()
        assert event.payload in compiled.params.values()

    asyncio.run(run())


def test_publisher_claims_and_marks_event_after_publish() -> None:
    async def run() -> None:
        event = make_event()
        statements: list[Any] = []

        class Session:
            def begin(self) -> TransactionContext:
                return TransactionContext()

            async def execute(self, statement: Any) -> Any:
                statements.append(statement)
                if len(statements) == 1:
                    row = {
                        "id": event.id,
                        "event_type": event.event_type,
                        "exchange": event.exchange,
                        "routing_key": event.routing_key,
                        "payload": event.payload,
                        "occurred_at": event.occurred_at,
                    }
                    return MagicMock(mappings=lambda: MagicMock(all=lambda: [row]))
                return MagicMock()

        published: list[OutboxMessage] = []

        async def publish(item: OutboxMessage) -> None:
            published.append(item)

        publisher = OutboxPublisher(
            cast(
                async_sessionmaker[AsyncSession],
                lambda: SessionContext(Session()),
            ),
            publish,
            exchange="artists.events",
        )

        assert await publisher.publish_batch() == 1
        assert published == [event]
        assert len(statements) == 2

        compiled = statements[0].compile(dialect=POSTGRES_DIALECT)
        assert "FOR UPDATE SKIP LOCKED" in str(compiled)
        assert "artists.events" in compiled.params.values()

    asyncio.run(run())


def test_publisher_does_not_mark_event_when_publish_fails() -> None:
    async def run() -> None:
        event = make_event()

        class Session:
            def begin(self) -> TransactionContext:
                return TransactionContext()

            async def execute(self, statement: Any) -> Any:
                row = {
                    "id": event.id,
                    "event_type": event.event_type,
                    "exchange": event.exchange,
                    "routing_key": event.routing_key,
                    "payload": event.payload,
                    "occurred_at": event.occurred_at,
                }
                return MagicMock(mappings=lambda: MagicMock(all=lambda: [row]))

        async def fail(_: OutboxMessage) -> None:
            raise RuntimeError("RabbitMQ is unavailable")

        publisher = OutboxPublisher(
            cast(
                async_sessionmaker[AsyncSession],
                lambda: SessionContext(Session()),
            ),
            fail,
            exchange="artists.events",
        )

        with pytest.raises(RuntimeError, match="RabbitMQ"):
            await publisher.publish_batch()

    asyncio.run(run())
