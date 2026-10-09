import asyncio
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.releases.errors import ReleaseNotDraftError
from yn.modules.tracks.dto import TrackDTO
from yn.modules.tracks.errors import (
    InvalidTrackFeaturesError,
    TrackNotFoundError,
    TrackUploadFailedError,
)
from yn.modules.tracks.schemas import TrackRead
from yn.modules.tracks.service import TrackService
from yn.modules.tracks.uploader import TrackUploadPayload, TrackUploadProcessor
from yn.modules.tracks.validation import validate_featured_artists
from yn.shared.settings import settings


def make_track(*, featured_artists: list[object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        release_id=uuid4(),
        title="Snow",
        duration_seconds=120,
        track_number_in_release=1,
        path="snow.mp3",
        genres=["ambient"],
        featured_artists=featured_artists or [],
        created_at=None,
        deleted_at=None,
    )


def make_service(
    track: SimpleNamespace, *, artists: list[object] | None = None
) -> tuple[TrackService, SimpleNamespace, SimpleNamespace]:
    uow = SimpleNamespace(
        artists=SimpleNamespace(
            get_artists_by_ids=AsyncMock(return_value=artists or [])
        ),
        tracks=SimpleNamespace(
            get_track_by_id_for_artist=AsyncMock(return_value=track),
            get_conflicting_track_for_release=AsyncMock(return_value=None),
            update=AsyncMock(return_value=track),
            create=AsyncMock(return_value=track),
        ),
        outbox=SimpleNamespace(add=AsyncMock()),
        commit=AsyncMock(),
    )
    releases = SimpleNamespace(get_owned_draft_release_by_id=AsyncMock())
    return TrackService(cast(Any, uow), cast(Any, releases)), uow, releases


@pytest.mark.parametrize("invalid", ["self", "duplicate"])
def test_features_reject_self_and_duplicates_without_querying_database(
    invalid: str,
) -> None:
    artist_id = uuid4()
    guest_id = uuid4()
    ids = [artist_id] if invalid == "self" else [guest_id, guest_id]
    _, uow, _ = make_service(make_track())

    with pytest.raises(InvalidTrackFeaturesError):
        asyncio.run(
            validate_featured_artists(
                cast(Any, uow), artist_id=artist_id, featured_artist_ids=ids
            )
        )

    uow.artists.get_artists_by_ids.assert_not_awaited()


def test_update_rejects_missing_or_deleted_featured_artist() -> None:
    track = make_track()
    service, uow, _ = make_service(track)

    with pytest.raises(ArtistNotFoundError):
        asyncio.run(
            service.update_track(
                track_id=track.id, artist_id=uuid4(), featured_artist_ids=[uuid4()]
            )
        )

    uow.tracks.update.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.parametrize("clear", [False, True])
def test_features_can_be_replaced_or_cleared_without_other_changes(
    monkeypatch: pytest.MonkeyPatch, clear: bool
) -> None:
    monkeypatch.setattr(settings, "discovery_enabled", True)
    guest = SimpleNamespace(id=uuid4(), displayed_name="Guest", deleted_at=None)
    track = make_track(featured_artists=[] if clear else [guest])
    service, uow, releases = make_service(track, artists=[guest])
    ids = [] if clear else [guest.id]
    owner_id = uuid4()

    result = asyncio.run(
        service.update_track(
            track_id=track.id, artist_id=owner_id, featured_artist_ids=ids
        )
    )

    assert [artist.id for artist in result.featured_artists] == ids
    assert uow.tracks.update.await_args.kwargs["featured_artist_ids"] == ids
    releases.get_owned_draft_release_by_id.assert_awaited_once_with(
        release_id=track.release_id, artist_id=owner_id
    )
    uow.outbox.add.assert_awaited_once()
    uow.commit.assert_awaited_once()
    if clear:
        uow.artists.get_artists_by_ids.assert_not_awaited()


def test_updating_title_keeps_features_unchanged() -> None:
    guest = SimpleNamespace(id=uuid4(), displayed_name="Guest", deleted_at=None)
    track = make_track(featured_artists=[guest])
    service, uow, _ = make_service(track)

    result = asyncio.run(
        service.update_track(track_id=track.id, artist_id=uuid4(), title="New title")
    )

    assert result.featured_artists[0].id == guest.id
    assert uow.tracks.update.await_args.kwargs["featured_artist_ids"] is None
    uow.artists.get_artists_by_ids.assert_not_awaited()


@pytest.mark.parametrize("forbidden", ["guest", "published"])
def test_features_do_not_grant_edit_rights_or_allow_editing_published_track(
    forbidden: str,
) -> None:
    track = make_track()
    service, uow, releases = make_service(track)
    error: type[Exception]
    if forbidden == "guest":
        uow.tracks.get_track_by_id_for_artist.return_value = None
        error = TrackNotFoundError
    else:
        releases.get_owned_draft_release_by_id.side_effect = ReleaseNotDraftError
        error = ReleaseNotDraftError

    with pytest.raises(error):
        asyncio.run(
            service.update_track(
                track_id=track.id, artist_id=uuid4(), featured_artist_ids=[]
            )
        )

    uow.tracks.update.assert_not_awaited()
    uow.commit.assert_not_awaited()


def test_track_response_includes_active_features() -> None:
    guest = SimpleNamespace(id=uuid4(), displayed_name="Guest", deleted_at=None)
    deleted_guest = SimpleNamespace(
        id=uuid4(), displayed_name="Deleted", deleted_at=datetime.now()
    )
    track = make_track(featured_artists=[guest, deleted_guest])

    response = TrackRead.model_validate(TrackDTO.from_orm(cast(Any, track)))

    assert [artist.id for artist in response.featured_artists] == [guest.id]
    assert response.featured_artists[0].displayed_name == "Guest"


def make_payload(
    *, featured_artist_ids: list[UUID] | None = None
) -> TrackUploadPayload:
    return TrackUploadPayload(
        track_id=uuid4(),
        release_id=uuid4(),
        current_artist_id=uuid4(),
        title="Snow",
        track_number_in_release=1,
        genres=["ambient"],
        storage_key="snow.mp3",
        temp_path="/tmp/snow.mp3",
        featured_artist_ids=featured_artist_ids or [],
    )


def test_upload_payload_preserves_features_and_accepts_old_messages() -> None:
    payload = make_payload(featured_artist_ids=[uuid4(), uuid4()])
    message = payload.to_message()

    assert TrackUploadPayload.from_message(message) == payload
    del message["featured_artist_ids"]
    assert TrackUploadPayload.from_message(message).featured_artist_ids == []


def test_upload_passes_features_to_the_queue() -> None:
    async def run() -> None:
        guest = SimpleNamespace(id=uuid4())
        service, _, _ = make_service(make_track(), artists=[guest])
        with (
            patch(
                "yn.modules.tracks.service.copy_upload_to_shared_tempfile",
                new_callable=AsyncMock,
                return_value="/tmp/snow.mp3",
            ),
            patch(
                "yn.modules.tracks.service.process_track_upload.kiq",
                new_callable=AsyncMock,
            ) as enqueue,
        ):
            result = await service.upload_track(
                release_id=uuid4(),
                current_artist_id=uuid4(),
                title="Snow",
                track_number_in_release=1,
                genres=[],
                file=cast(UploadFile, SimpleNamespace(filename="snow.mp3")),
                featured_artist_ids=[guest.id],
            )

        assert enqueue.await_args is not None
        queued = TrackUploadPayload.from_message(enqueue.await_args.kwargs["payload"])
        assert queued.featured_artist_ids == [guest.id]
        assert result.featured_artist_ids == [guest.id]

    asyncio.run(run())


def test_upload_worker_revalidates_features_before_uploading() -> None:
    async def run() -> None:
        payload = make_payload(featured_artist_ids=[uuid4()])
        _, uow, releases = make_service(make_track())
        processor = TrackUploadProcessor(
            cast(Any, uow), cast(Any, None), cast(Any, releases)
        )
        with (
            patch.object(
                processor, "_read_duration_seconds", new_callable=AsyncMock
            ) as read_audio,
            patch.object(
                processor, "_safe_delete_from_storage", new_callable=AsyncMock
            ),
            patch.object(
                processor, "_cleanup_tempfile", new_callable=AsyncMock
            ) as cleanup,
        ):
            with pytest.raises(TrackUploadFailedError) as error:
                await processor.process(payload)

        assert isinstance(error.value.__cause__, ArtistNotFoundError)
        read_audio.assert_not_awaited()
        uow.tracks.create.assert_not_awaited()
        uow.commit.assert_not_awaited()
        cleanup.assert_awaited_once_with(payload.temp_path)

    asyncio.run(run())


def test_upload_worker_persists_features_with_the_track() -> None:
    async def run() -> None:
        guest = SimpleNamespace(id=uuid4(), displayed_name="Guest", deleted_at=None)
        payload = make_payload(featured_artist_ids=[guest.id])
        _, uow, releases = make_service(
            make_track(featured_artists=[guest]), artists=[guest]
        )
        processor = TrackUploadProcessor(
            cast(Any, uow), cast(Any, None), cast(Any, releases)
        )
        with (
            patch.object(
                processor,
                "_read_duration_seconds",
                new_callable=AsyncMock,
                return_value=120,
            ),
            patch.object(processor, "_upload_to_storage", new_callable=AsyncMock),
            patch.object(processor, "_cleanup_tempfile", new_callable=AsyncMock),
        ):
            result = await processor.process(payload)

        assert uow.tracks.create.await_args.kwargs["featured_artist_ids"] == [guest.id]
        assert result.featured_artists[0].id == guest.id
        uow.commit.assert_awaited_once()

    asyncio.run(run())
