import asyncio
import math
import shutil
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from yn.modules.albums.service import AlbumService
from yn.modules.tracks.dto import TrackDTO
from yn.modules.tracks.errors import (
    TrackConflictError,
    TrackFormatError,
    TrackMetadataError,
    TrackUploadFailedError,
)
from yn.shared.minio import MinioStorage
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork

ALLOWED_TRACK_SUFFIXES = {".mp3", ".wav"}


@dataclass(slots=True)
class TrackUploadPayload:
    track_id: UUID
    album_id: UUID
    current_profile_id: UUID
    title: str
    genres: list[str]
    storage_key: str
    temp_path: str

    def to_message(self) -> dict[str, object]:
        return {
            "track_id": str(self.track_id),
            "album_id": str(self.album_id),
            "current_profile_id": str(self.current_profile_id),
            "title": self.title,
            "genres": self.genres,
            "storage_key": self.storage_key,
            "temp_path": self.temp_path,
        }

    @classmethod
    def from_message(cls, payload: dict[str, object]) -> "TrackUploadPayload":
        genres_value = payload.get("genres", [])
        if isinstance(genres_value, Sequence) and not isinstance(
            genres_value, (str, bytes)
        ):
            genres = [str(genre) for genre in genres_value]
        else:
            genres = []

        return cls(
            track_id=UUID(str(payload["track_id"])),
            album_id=UUID(str(payload["album_id"])),
            current_profile_id=UUID(str(payload["current_profile_id"])),
            title=str(payload["title"]),
            genres=genres,
            storage_key=str(payload["storage_key"]),
            temp_path=str(payload["temp_path"]),
        )


def validate_track_filename(filename: str | None) -> None:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_TRACK_SUFFIXES:
        raise TrackFormatError


def build_track_storage_key(
    *, album_id: UUID, track_id: UUID, filename: str | None
) -> str:
    suffix = Path(filename or "").suffix.lower()
    return f"{album_id}/{track_id}{suffix}"


async def copy_upload_to_shared_tempfile(file: UploadFile) -> str:
    await file.seek(0)
    Path(settings.upload_temp_dir).mkdir(parents=True, exist_ok=True)

    def write_tempfile() -> str:
        with tempfile.NamedTemporaryFile(
            dir=settings.upload_temp_dir, delete=False
        ) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            return temp_file.name

    return await asyncio.to_thread(write_tempfile)


class TrackUploadProcessor:
    def __init__(
        self, uow: UnitOfWork, storage: MinioStorage, album_service: AlbumService
    ):
        self.uow = uow
        self.storage = storage
        self.album_service = album_service

    async def process(self, payload: TrackUploadPayload) -> TrackDTO:
        await self.album_service.get_owned_draft_album_by_id(
            album_id=payload.album_id,
            profile_id=payload.current_profile_id,
        )

        track = None
        try:
            duration_seconds = await self._read_duration_seconds(payload.temp_path)
            await self._upload_to_storage(
                storage_key=payload.storage_key, temp_path=payload.temp_path
            )
            track = await self.uow.tracks.create(
                track_id=payload.track_id,
                album_id=payload.album_id,
                title=payload.title,
                duration_seconds=duration_seconds,
                path=payload.storage_key,
                genres=payload.genres,
            )
        except TrackConflictError:
            await self._safe_delete_from_storage(payload.storage_key)
            raise
        except Exception as exc:
            await self._safe_delete_from_storage(payload.storage_key)
            if isinstance(exc, TrackMetadataError):
                raise
            raise TrackUploadFailedError from exc
        finally:
            await self._cleanup_tempfile(payload.temp_path)

        return TrackDTO.from_orm(track)

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
