from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from yn.modules.albums.service import AlbumService
from yn.modules.tracks.dto import TrackUploadQueuedDTO
from yn.modules.tracks.errors import TrackConflictError, TrackUploadFailedError
from yn.modules.tracks.uploader import (
    TrackUploadPayload,
    build_track_storage_key,
    copy_upload_to_shared_tempfile,
    validate_track_filename,
)
from yn.shared.unit_of_work import UnitOfWork
from yn.tasks.track_upload import process_track_upload


class TrackService:
    def __init__(self, uow: UnitOfWork, album_service: AlbumService):
        self.uow = uow
        self.album_service = album_service

    async def upload_track(
        self,
        *,
        album_id: UUID,
        current_profile_id: UUID,
        title: str,
        genres: list[str],
        file: UploadFile,
    ) -> TrackUploadQueuedDTO:
        await self.album_service.get_owned_draft_album_by_id(
            album_id=album_id,
            profile_id=current_profile_id,
        )

        validate_track_filename(file.filename)
        await self._ensure_track_title_is_available(album_id=album_id, title=title)

        track_id = uuid4()
        storage_key = build_track_storage_key(
            album_id=album_id,
            track_id=track_id,
            filename=file.filename,
        )
        temp_path = await copy_upload_to_shared_tempfile(file)

        try:
            await process_track_upload.kiq(
                payload=TrackUploadPayload(
                    track_id=track_id,
                    album_id=album_id,
                    current_profile_id=current_profile_id,
                    title=title,
                    genres=genres,
                    storage_key=storage_key,
                    temp_path=temp_path,
                ).to_message()
            )
        except Exception as exc:
            await self._cleanup_tempfile(temp_path)
            raise TrackUploadFailedError from exc

        return TrackUploadQueuedDTO(track_id=track_id, album_id=album_id, title=title)

    async def _ensure_track_title_is_available(
        self, *, album_id: UUID, title: str
    ) -> None:
        track = await self.uow.tracks.get_track_by_album_and_title(album_id, title)
        if track is not None:
            raise TrackConflictError

    async def _cleanup_tempfile(self, temp_path: str) -> None:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
