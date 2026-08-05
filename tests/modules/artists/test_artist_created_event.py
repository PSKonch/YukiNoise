import asyncio
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from yn.modules.artists.errors import ArtistAlreadyExistsError, ArtistConflictError
from yn.modules.artists.events import ARTIST_EVENTS_TOPIC, ArtistCreatedEvent
from yn.modules.artists.service import ArtistService
from yn.shared.publisher import KafkaPublisher


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


def test_create_artist_publishes_event() -> None:
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
        publisher = AsyncMock(spec=KafkaPublisher)
        uow = SimpleNamespace(
            artists=SimpleNamespace(create=AsyncMock(return_value=artist)),
        )
        service = ArtistService(
            cast(Any, uow),
            cast(Any, SimpleNamespace()),
            cast(Any, SimpleNamespace()),
            cast(KafkaPublisher, publisher),
        )

        result = await service.create_artist(user_id, "Artist")

        assert result.id == artist_id
        publisher.publish.assert_awaited_once()
        event = publisher.publish.await_args.kwargs["message"]
        assert isinstance(event, ArtistCreatedEvent)
        assert event.artist_id == artist_id
        assert event.user_id == user_id
        assert event.displayed_name == "Artist"
        assert publisher.publish.await_args.kwargs == {
            "message": event,
            "key": artist_id,
            "headers": {
                "event-type": "artist.created",
                "event-version": "1",
            },
            "correlation_id": str(event.event_id),
        }

    asyncio.run(run())


def test_artist_events_topic_is_stable() -> None:
    assert ARTIST_EVENTS_TOPIC == "artists.events"


def test_create_artist_does_not_publish_event_on_conflict() -> None:
    async def run() -> None:
        publisher = AsyncMock(spec=KafkaPublisher)
        artists = SimpleNamespace(
            create=AsyncMock(side_effect=ArtistConflictError),
            get_artist_conflict_flags=AsyncMock(return_value=(True, False)),
        )
        service = ArtistService(
            cast(Any, SimpleNamespace(artists=artists)),
            cast(Any, SimpleNamespace()),
            cast(Any, SimpleNamespace()),
            cast(KafkaPublisher, publisher),
        )

        with pytest.raises(ArtistAlreadyExistsError):
            await service.create_artist(uuid4(), "Artist")

        publisher.publish.assert_not_awaited()

    asyncio.run(run())
