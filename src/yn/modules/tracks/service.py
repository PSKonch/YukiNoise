from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from yn.modules.releases.service import ReleaseService
from yn.modules.tracks.dto import TrackDTO, TrackUploadQueuedDTO
from yn.modules.tracks.errors import (
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
        await self._ensure_track_title_is_available(release_id=release_id, title=title)
        await self._ensure_track_number_is_available(
            release_id=release_id,
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

    # Validation helpers
    async def _ensure_track_title_is_available(
        self, *, release_id: UUID, title: str
    ) -> None:
        track = await self.uow.tracks.get_track_by_release_and_title(release_id, title)
        if track is not None:
            raise TrackConflictError

    async def _ensure_track_number_is_available(
        self, *, release_id: UUID, track_number_in_release: int
    ) -> None:
        track = await self.uow.tracks.get_track_by_release_and_number(
            release_id, track_number_in_release
        )
        if track is not None:
            raise TrackConflictError

    async def _cleanup_tempfile(self, temp_path: str) -> None:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
