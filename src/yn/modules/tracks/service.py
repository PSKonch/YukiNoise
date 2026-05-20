import asyncio
import math
import shutil
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from yn.modules.albums.service import AlbumService
from yn.modules.tracks.dto import TrackDTO
from yn.modules.tracks.errors import TrackMetadataError, TrackUploadFailedError
from yn.shared.minio import MinioStorage
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork


class TrackService:
    def __init__(
        self, uow: UnitOfWork, storage: MinioStorage, album_service: AlbumService
    ):
        self.uow = uow
        self.storage = storage
        self.album_service = album_service

    async def upload_track(
        self,
        *,
        album_id: UUID,
        current_profile_id: UUID,
        title: str,
        genres: list[str],
        file: UploadFile,
    ) -> TrackDTO:
        await self.album_service.get_owned_album_by_id(
            album_id=album_id,
            profile_id=current_profile_id,
        )

        track_id = uuid4()
        storage_key = self._build_storage_key(
            album_id=album_id, track_id=track_id, file=file
        )
        temp_path = await self._copy_upload_to_tempfile(file)

        try:
            duration_seconds = await self._read_duration_seconds(temp_path)
            await self._upload_to_storage(storage_key=storage_key, temp_path=temp_path)
            track = await self.uow.tracks.create(
                track_id=track_id,
                album_id=album_id,
                title=title,
                duration_seconds=duration_seconds,
                path=storage_key,
                genres=genres,
            )
        except IntegrityError as exc:
            await self._safe_delete_from_storage(storage_key)
            raise TrackUploadFailedError from exc
        except Exception as exc:
            await self._safe_delete_from_storage(storage_key)
            if isinstance(exc, TrackMetadataError):
                raise
            raise TrackUploadFailedError from exc
        finally:
            await self._cleanup_tempfile(temp_path)

        return TrackDTO.from_orm(track)

    def _build_storage_key(
        self, *, album_id: UUID, track_id: UUID, file: UploadFile
    ) -> str:
        suffix = Path(file.filename or "").suffix
        return f"{album_id}/{track_id}{suffix}"

    async def _copy_upload_to_tempfile(self, file: UploadFile) -> str:
        await file.seek(0)

        def write_tempfile() -> str:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                shutil.copyfileobj(file.file, temp_file)
                return temp_file.name

        return await asyncio.to_thread(write_tempfile)

    async def _upload_to_storage(self, *, storage_key: str, temp_path: str) -> None:
        with Path(temp_path).open("rb") as stream:
            await self.storage.put(settings.minio_bucket, storage_key, stream)

    async def _read_duration_seconds(self, temp_path: str) -> int:
        try:
            process = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise TrackMetadataError("ffprobe is not installed") from exc

        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            message = (
                stderr.decode().strip() or stdout.decode().strip() or "ffprobe failed"
            )
            raise TrackMetadataError(message)

        duration_text = stdout.decode().strip()
        if not duration_text:
            raise TrackMetadataError("Audio duration is empty")

        try:
            return max(1, int(math.ceil(float(duration_text))))
        except ValueError as exc:
            raise TrackMetadataError("Audio duration is invalid") from exc

    async def _safe_delete_from_storage(self, storage_key: str) -> None:
        try:
            await self.storage.delete(settings.minio_bucket, storage_key)
        except Exception:
            pass

    async def _cleanup_tempfile(self, temp_path: str) -> None:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
