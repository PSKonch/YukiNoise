import asyncio
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from yn.modules.artists.errors import ArtistAlreadyExistsError, ArtistConflictError
from yn.modules.artists.events import ARTIST_EVENTS_TOPIC, ArtistCreatedEvent
from yn.modules.artists.service import ArtistService
from yn.shared.outbox.publisher import OutboxPublisher


def test_artist_created_event_round_trip() -> None:
    event = ArtistCreatedEvent(
        artist_id=uuid4(),
        user_id=uuid4(),
        displayed_name="Artist",
    )

    restored = ArtistCreatedEvent.model_validate_json(event.model_dump_json())

    assert restored == event
    assert restored.event_type == "artist.created"
    assert restored.version == 1


def test_create_artist_commits_event_to_outbox_before_immediate_publish() -> None:
    async def run() -> None:
        artist_id = uuid4()
        user_id = uuid4()
        artist = SimpleNamespace(
            id=artist_id,
            user_id=user_id,
            displayed_name="Artist",
            bio=None,
            social_links=None,
        )
        call_order: list[str] = []
        publisher = AsyncMock(spec=OutboxPublisher)
        publisher.publish_now.side_effect = lambda *_: call_order.append("publish")
        outbox = SimpleNamespace(
            add=AsyncMock(side_effect=lambda **_: call_order.append("outbox"))
        )
        uow = SimpleNamespace(
            artists=SimpleNamespace(create=AsyncMock(return_value=artist)),
            outbox=outbox,
            commit=AsyncMock(side_effect=lambda: call_order.append("commit")),
            rollback=AsyncMock(),
        )
        service = ArtistService(
            cast(Any, uow),
            cast(Any, SimpleNamespace()),
            cast(Any, SimpleNamespace()),
            cast(OutboxPublisher, publisher),
        )

        result = await service.create_artist(user_id, "Artist")

        assert result.id == artist_id
        uow.commit.assert_awaited_once()
        outbox.add.assert_awaited_once()
        assert call_order == ["outbox", "commit", "publish"]
        outbox_values = outbox.add.await_args.kwargs
        event = ArtistCreatedEvent.model_validate(outbox_values["payload"])
        assert event.artist_id == artist_id
        assert event.user_id == user_id
        assert event.displayed_name == "Artist"
        assert outbox_values == {
            "event_id": event.event_id,
            "topic": ARTIST_EVENTS_TOPIC,
            "message_key": str(artist_id),
            "event_type": "artist.created",
            "version": 1,
            "payload": event.model_dump(mode="json"),
        }
        publisher.publish_now.assert_awaited_once_with(event.event_id)

    asyncio.run(run())


def test_artist_events_topic_is_stable() -> None:
    assert ARTIST_EVENTS_TOPIC == "artists.events"


def test_create_artist_does_not_publish_before_transaction_commits() -> None:
    async def run() -> None:
        artist_id = uuid4()
        user_id = uuid4()
        artist = SimpleNamespace(
            id=artist_id,
            user_id=user_id,
            displayed_name="Artist",
            bio=None,
            social_links=None,
        )
        publisher = AsyncMock(spec=OutboxPublisher)
        uow = SimpleNamespace(
            artists=SimpleNamespace(create=AsyncMock(return_value=artist)),
            outbox=SimpleNamespace(add=AsyncMock()),
            commit=AsyncMock(side_effect=RuntimeError("commit failed")),
            rollback=AsyncMock(),
        )
        service = ArtistService(
            cast(Any, uow),
            cast(Any, SimpleNamespace()),
            cast(Any, SimpleNamespace()),
            cast(OutboxPublisher, publisher),
        )

        with pytest.raises(RuntimeError, match="commit failed"):
            await service.create_artist(user_id, "Artist")

        uow.outbox.add.assert_awaited_once()
        publisher.publish_now.assert_not_awaited()

    asyncio.run(run())


def test_create_artist_does_not_publish_event_on_conflict() -> None:
    async def run() -> None:
        publisher = AsyncMock(spec=OutboxPublisher)
        outbox = SimpleNamespace(add=AsyncMock())
        artists = SimpleNamespace(
            create=AsyncMock(side_effect=ArtistConflictError),
            get_artist_conflict_flags=AsyncMock(return_value=(True, False)),
        )
        uow = SimpleNamespace(
            artists=artists,
            outbox=outbox,
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )
        service = ArtistService(
            cast(Any, uow),
            cast(Any, SimpleNamespace()),
            cast(Any, SimpleNamespace()),
            cast(OutboxPublisher, publisher),
        )

        with pytest.raises(ArtistAlreadyExistsError):
            await service.create_artist(uuid4(), "Artist")

        uow.rollback.assert_awaited_once()
        uow.commit.assert_not_awaited()
        outbox.add.assert_not_awaited()
        publisher.publish_now.assert_not_awaited()

    asyncio.run(run())
