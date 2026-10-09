import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, PropertyMock, patch
from uuid import UUID, uuid4

import pytest
from faststream.middlewares import AckPolicy
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.notifications.kafka import (
    NOTIFICATIONS_RELEASE_EVENTS_GROUP,
    notify_release_followers,
    router,
)
from yn.modules.notifications.repository import ReleaseNotificationSource
from yn.modules.releases.events import (
    RELEASE_EVENTS_TOPIC,
    ReleasePublishedEvent,
    record_release_published,
)
from yn.shared.unit_of_work import UnitOfWork


def test_publication_event_is_saved_without_committing_or_publishing() -> None:
    async def run() -> None:
        uow = SimpleNamespace(
            outbox=SimpleNamespace(add=AsyncMock()), commit=AsyncMock()
        )
        release_id = uuid4()
        await record_release_published(cast(UnitOfWork, uow), release_id)
        values = uow.outbox.add.await_args.kwargs
        event = ReleasePublishedEvent.model_validate(values["payload"])
        assert event.release_id == release_id
        assert event.occurred_at.tzinfo is not None
        assert values["topic"] == RELEASE_EVENTS_TOPIC
        assert values["message_key"] == str(release_id)
        uow.commit.assert_not_awaited()

    asyncio.run(run())


def test_delivery_pages_recipients_and_propagates_failures_for_redelivery() -> None:
    async def run() -> None:
        event = ReleasePublishedEvent(release_id=uuid4())
        ids = [UUID(int=value) for value in (1, 2, 3)]
        source = ReleaseNotificationSource(event.release_id, uuid4(), "Winter", "Snow")
        repo = SimpleNamespace(
            get_release_source=AsyncMock(return_value=source),
            get_recipient_ids=AsyncMock(side_effect=[ids[:2], ids[2:]]),
            add_release_notifications=AsyncMock(side_effect=[None, RuntimeError("DB")]),
        )
        sessions: list[AsyncSession] = []

        @asynccontextmanager
        async def factory() -> AsyncIterator[AsyncSession]:
            session = AsyncMock(spec=AsyncSession)
            sessions.append(session)
            yield session

        with patch.object(
            UnitOfWork, "notifications", new_callable=PropertyMock
        ) as prop:
            prop.return_value = repo
            with pytest.raises(RuntimeError, match="DB"):
                await notify_release_followers(event, factory, batch_size=2)
        assert [
            call.kwargs["after"] for call in repo.get_recipient_ids.await_args_list
        ] == [None, ids[1]]
        cast(Any, sessions[0]).commit.assert_awaited_once()
        cast(Any, sessions[1]).commit.assert_not_awaited()
        cast(Any, sessions[1]).rollback.assert_awaited_once()

    asyncio.run(run())


def test_missing_or_hidden_release_does_not_notify_anyone() -> None:
    async def run() -> None:
        repo = SimpleNamespace(
            get_release_source=AsyncMock(return_value=None),
            get_recipient_ids=AsyncMock(),
        )

        @asynccontextmanager
        async def factory() -> AsyncIterator[AsyncSession]:
            yield AsyncMock(spec=AsyncSession)

        with patch.object(
            UnitOfWork, "notifications", new_callable=PropertyMock
        ) as prop:
            prop.return_value = repo
            await notify_release_followers(
                ReleasePublishedEvent(release_id=uuid4()), factory
            )
        repo.get_recipient_ids.assert_not_awaited()

    asyncio.run(run())


def test_consumer_has_an_independent_group_and_retries_on_error() -> None:
    subscriber = next(cast(Any, item) for item in router.subscribers)
    assert subscriber.topics == [RELEASE_EVENTS_TOPIC]
    assert subscriber.group_id == NOTIFICATIONS_RELEASE_EVENTS_GROUP
    assert subscriber.ack_policy is AckPolicy.NACK_ON_ERROR
