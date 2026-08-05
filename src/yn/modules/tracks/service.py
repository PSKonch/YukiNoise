from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import UploadFile

from yn.modules.releases.service import ReleaseService
from yn.modules.tracks.dto import TrackDTO, TrackUploadQueuedDTO
from yn.modules.tracks.errors import (
    EmptyTrackUpdateError,
    TrackConflictError,
    TrackNotFoundError,
    TrackUploadFailedError,
)
from yn.modules.tracks.uploader import (
    TrackUploadPayload,
    build_track_storage_key,
    copy_upload_to_shared_tempfile,
    validate_track_filename,
    validate_track_number_in_release,
)
from yn.shared.unit_of_work import UnitOfWork
from yn.tasks.track_upload import process_track_upload

if TYPE_CHECKING:
    from yn.modules.tracks.model import Track


class TrackService:
    def __init__(self, uow: UnitOfWork, release_service: ReleaseService):
        self.uow = uow
        self.release_service = release_service

    # Public read
    async def get_tracks(self, *, limit: int, offset: int) -> list[TrackDTO]:
        tracks = await self.uow.tracks.get_tracks(limit=limit, offset=offset)
        return [TrackDTO.from_orm(track) for track in tracks]

    async def get_track_by_id(self, track_id: UUID) -> TrackDTO:
        track = await self.uow.tracks.get_track_by_id(track_id)
        if track is None:
            raise TrackNotFoundError
        return TrackDTO.from_orm(track)

    async def get_tracks_by_artist_id(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[TrackDTO]:
        tracks = await self.uow.tracks.get_tracks_by_artist_id(
            artist_id=artist_id,
            limit=limit,
            offset=offset,
        )
        return [TrackDTO.from_orm(track) for track in tracks]

    # Owner read
    async def get_owned_tracks_by_artist_id(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[TrackDTO]:
        tracks = await self.uow.tracks.get_owned_tracks_by_artist_id(
            artist_id=artist_id,
            limit=limit,
            offset=offset,
        )
        return [TrackDTO.from_orm(track) for track in tracks]

    async def get_owned_track_by_id(self, track_id: UUID, artist_id: UUID) -> TrackDTO:
        track = await self._get_owned_track(track_id=track_id, artist_id=artist_id)
        return TrackDTO.from_orm(track)

    # Owner write
    async def upload_track(
        self,
        *,
        release_id: UUID,
        current_artist_id: UUID,
        title: str,
        track_number_in_release: int,
        genres: list[str],
        file: UploadFile,
    ) -> TrackUploadQueuedDTO:
        await self.release_service.get_owned_draft_release_by_id(
            release_id=release_id,
            artist_id=current_artist_id,
        )

        validate_track_number_in_release(track_number_in_release)
        validate_track_filename(file.filename)
        await self._ensure_track_is_available(
            release_id=release_id,
            title=title,
            track_number_in_release=track_number_in_release,
        )

        track_id = uuid4()
        storage_key = build_track_storage_key(
            release_id=release_id,
            track_id=track_id,
            filename=file.filename,
        )
        temp_path = await copy_upload_to_shared_tempfile(file)

        try:
            await process_track_upload.kiq(
                payload=TrackUploadPayload(
                    track_id=track_id,
                    release_id=release_id,
                    current_artist_id=current_artist_id,
                    title=title,
                    track_number_in_release=track_number_in_release,
                    genres=genres,
                    storage_key=storage_key,
                    temp_path=temp_path,
                ).to_message()
            )
        except Exception as exc:
            await self._cleanup_tempfile(temp_path)
            raise TrackUploadFailedError from exc

        return TrackUploadQueuedDTO(
            track_id=track_id,
            release_id=release_id,
            title=title,
            track_number_in_release=track_number_in_release,
        )

    async def update_track(
        self,
        *,
        track_id: UUID,
        artist_id: UUID,
        title: str | None = None,
        track_number_in_release: int | None = None,
        genres: list[str] | None = None,
    ) -> TrackDTO:
        if title is None and track_number_in_release is None and genres is None:
            raise EmptyTrackUpdateError

        track = await self._get_owned_track(track_id=track_id, artist_id=artist_id)
        await self.release_service.get_owned_draft_release_by_id(
            release_id=track.release_id,
            artist_id=artist_id,
        )

        if track_number_in_release is not None:
            validate_track_number_in_release(track_number_in_release)

        updated = await self.uow.tracks.update(
            track_id=track.id,
            release_id=track.release_id,
            title=title,
            track_number_in_release=track_number_in_release,
            genres=genres,
        )
        if updated is None:
            raise TrackNotFoundError
        await self.uow.commit()
        return TrackDTO.from_orm(updated)

    async def delete_track(self, track_id: UUID, artist_id: UUID) -> None:
        track = await self._get_owned_track(track_id=track_id, artist_id=artist_id)
        await self.release_service.get_owned_draft_release_by_id(
            release_id=track.release_id,
            artist_id=artist_id,
        )
        deleted = await self.uow.tracks.soft_delete(
            track_id=track.id,
            release_id=track.release_id,
        )
        if not deleted:
            raise TrackNotFoundError
        await self.uow.commit()

    # Validation helpers
    async def _ensure_track_is_available(
        self,
        *,
        release_id: UUID,
        title: str,
        track_number_in_release: int,
    ) -> None:
        track = await self.uow.tracks.get_conflicting_track_for_release(
            release_id=release_id,
            title=title,
            track_number_in_release=track_number_in_release,
        )
        if track is not None:
            raise TrackConflictError

    async def _get_owned_track(self, *, track_id: UUID, artist_id: UUID) -> "Track":
        track = await self.uow.tracks.get_track_by_id_for_artist(
            track_id=track_id,
            artist_id=artist_id,
        )
        if track is None:
            raise TrackNotFoundError
        return track

    async def _cleanup_tempfile(self, temp_path: str) -> None:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
