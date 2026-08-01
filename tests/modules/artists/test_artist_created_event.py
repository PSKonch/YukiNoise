import asyncio
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

from yn.modules.artists.rmq.events import ArtistCreatedEvent
from yn.modules.artists.service import ArtistService


def test_artist_created_event_round_trip() -> None:
    event = ArtistCreatedEvent(artist_id=uuid4())

    restored = ArtistCreatedEvent.model_validate_json(event.model_dump_json())

    assert restored == event
    assert restored.event_type == "artist.created"
    assert restored.version == 1


def test_artist_and_event_are_added_to_the_same_unit_of_work() -> None:
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

        outbox = SimpleNamespace(add=AsyncMock())
        uow = SimpleNamespace(
            artists=SimpleNamespace(create=AsyncMock(return_value=artist)),
            outbox=outbox,
        )
        service = ArtistService(
            cast(Any, uow),
            cast(Any, SimpleNamespace()),
            cast(Any, SimpleNamespace()),
        )

        result = await service.create_artist(user_id, "Artist")

        assert result.id == artist_id
        outbox.add.assert_awaited_once()
        event_data = outbox.add.await_args.kwargs
        assert event_data["event_type"] == "artist.created"
        assert event_data["routing_key"] == "artist.created.v1"
        assert event_data["payload"]["artist_id"] == str(artist_id)

    asyncio.run(run())
