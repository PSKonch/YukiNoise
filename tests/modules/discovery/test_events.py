import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from pydantic import TypeAdapter

from yn.modules.discovery.events import (
    ArtistIndexRequestedEvent,
    IndexRequestedEvent,
    ReleaseIndexRequestedEvent,
    TrackIndexRequestedEvent,
    request_artist_index,
    request_release_index,
    request_track_index,
)
from yn.modules.discovery.kafka import consume_track_index_requested
from yn.modules.releases.service import ReleaseService
from yn.modules.tracks.service import TrackService
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork
from yn.tasks.index_track import index_source_embeddings, index_track_embedding


def test_index_events_use_transactional_outbox_and_are_disabled_with_feature_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        identifier = uuid4()
        outbox = SimpleNamespace(add=AsyncMock())
        uow = cast(UnitOfWork, SimpleNamespace(outbox=outbox, commit=AsyncMock()))
        monkeypatch.setattr(settings, "discovery_enabled", True)
        for request in (
            request_track_index,
            request_release_index,
            request_artist_index,
        ):
            await request(uow, identifier)
        adapter: TypeAdapter[IndexRequestedEvent] = TypeAdapter(IndexRequestedEvent)
        events = [
            adapter.validate_python(call.kwargs["payload"])
            for call in outbox.add.await_args_list
        ]
        assert [event.event_type for event in events] == [
            "track.index_requested",
            "release.index_requested",
            "artist.index_requested",
        ]
        assert all(
            call.kwargs["message_key"] == str(identifier)
            for call in outbox.add.await_args_list
        )
        cast(Any, uow).commit.assert_not_awaited()
        monkeypatch.setattr(settings, "discovery_enabled", False)
        outbox.add.reset_mock()
        await request_track_index(uow, identifier)
        await request_release_index(uow, identifier)
        await request_artist_index(uow, identifier)
        outbox.add.assert_not_awaited()

    asyncio.run(run())


def test_kafka_dispatches_track_release_and_artist_events_to_the_right_tasks() -> None:
    async def run() -> None:
        identifier = uuid4()
        with patch.object(
            index_track_embedding, "kiq", new_callable=AsyncMock
        ) as track_task:
            with patch.object(
                index_source_embeddings, "kiq", new_callable=AsyncMock
            ) as source_task:
                await consume_track_index_requested(
                    TrackIndexRequestedEvent(track_id=identifier)
                )
                await consume_track_index_requested(
                    ReleaseIndexRequestedEvent(release_id=identifier)
                )
                await consume_track_index_requested(
                    ArtistIndexRequestedEvent(artist_id=identifier)
                )
                track_task.assert_awaited_once_with(str(identifier))
                assert [call.args for call in source_task.await_args_list] == [
                    (str(identifier), "release"),
                    (str(identifier), "artist"),
                ]

    asyncio.run(run())


def test_track_update_records_event_before_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        monkeypatch.setattr(settings, "discovery_enabled", True)
        order: list[str] = []
        track = SimpleNamespace(
            id=uuid4(),
            release_id=uuid4(),
            title="Snow",
            duration_seconds=10,
            track_number_in_release=1,
            path="track.mp3",
            genres=["ambient"],
            created_at=None,
            deleted_at=None,
        )
        uow = SimpleNamespace(
            tracks=SimpleNamespace(
                get_track_by_id_for_artist=AsyncMock(return_value=track),
                update=AsyncMock(return_value=track),
            ),
            outbox=SimpleNamespace(
                add=AsyncMock(side_effect=lambda **_: order.append("event"))
            ),
            commit=AsyncMock(side_effect=lambda: order.append("commit")),
        )
        release_service = SimpleNamespace(get_owned_draft_release_by_id=AsyncMock())
        await TrackService(cast(Any, uow), cast(Any, release_service)).update_track(
            track_id=track.id, artist_id=uuid4(), title="New title"
        )
        assert order == ["event", "commit"]
        assert uow.outbox.add.await_args.kwargs["payload"]["track_id"] == str(track.id)

    asyncio.run(run())


@pytest.mark.parametrize("operation", ["description", "schedule", "unschedule"])
def test_release_changes_record_event_before_commit(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    async def run() -> None:
        monkeypatch.setattr(settings, "discovery_enabled", True)
        order: list[str] = []
        release = SimpleNamespace(
            id=uuid4(),
            artist_id=uuid4(),
            title="Winter",
            description=None,
            release_type="album",
            status="draft",
        )
        repository = SimpleNamespace(
            update_description=AsyncMock(return_value=release),
            schedule_release=AsyncMock(return_value=release),
            unschedule_release=AsyncMock(return_value=release),
        )
        uow = SimpleNamespace(
            releases=repository,
            outbox=SimpleNamespace(
                add=AsyncMock(side_effect=lambda **_: order.append("event"))
            ),
            commit=AsyncMock(side_effect=lambda: order.append("commit")),
        )
        service = ReleaseService(cast(Any, uow), cast(Any, None))
        if operation == "description":
            await service.update_description_of_release(
                release.artist_id, release.id, "New description"
            )
        elif operation == "schedule":
            await service.schedule_release(
                release_id=release.id,
                artist_id=release.artist_id,
                release_date=datetime.now(UTC) + timedelta(days=1),
            )
        else:
            await service.unschedule_release(
                release_id=release.id, artist_id=release.artist_id
            )
        assert order == ["event", "commit"]
        assert uow.outbox.add.await_args.kwargs["payload"]["release_id"] == str(
            release.id
        )

    asyncio.run(run())
