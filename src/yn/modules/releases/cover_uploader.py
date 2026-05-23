import asyncio
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from yn.modules.releases.errors import (
    ReleaseAccessDeniedError,
    ReleaseCoverUploadFailedError,
    ReleaseNotFoundError,
)
from yn.shared.minio import MinioStorage
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork


@dataclass(slots=True)
class ReleaseCoverUploadPayload:
    release_id: UUID
    profile_id: UUID
    cover_path: str
    temp_path: str

    def to_message(self) -> dict[str, object]:
        return {
            "release_id": str(self.release_id),
            "profile_id": str(self.profile_id),
            "cover_path": self.cover_path,
            "temp_path": self.temp_path,
        }

    @classmethod
    def from_message(cls, payload: dict[str, object]) -> "ReleaseCoverUploadPayload":
        return cls(
            release_id=UUID(str(payload["release_id"])),
            profile_id=UUID(str(payload["profile_id"])),
            cover_path=str(payload["cover_path"]),
            temp_path=str(payload["temp_path"]),
        )


def build_release_cover_storage_key(*, release_id: UUID, filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    return f"releases/{release_id}/cover{suffix}"


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


class ReleaseCoverUploadProcessor:
    def __init__(self, uow: UnitOfWork, storage: MinioStorage):
        self.uow = uow
        self.storage = storage

    async def process(self, payload: ReleaseCoverUploadPayload) -> None:
        release = await self.uow.releases.get_release_by_id(payload.release_id)
        if release is None:
            raise ReleaseNotFoundError
        if release.profile_id != payload.profile_id:
            raise ReleaseAccessDeniedError

        try:
            await self._upload_to_storage(
                storage_key=payload.cover_path, temp_path=payload.temp_path
            )
            updated_release = await self.uow.releases.update_cover_path(
                release_id=payload.release_id,
                profile_id=payload.profile_id,
                cover_path=payload.cover_path,
            )
        except Exception as exc:
            await self._safe_delete_from_storage(payload.cover_path)
            raise ReleaseCoverUploadFailedError from exc
        finally:
            await self._cleanup_tempfile(payload.temp_path)

        if updated_release is None:
            await self._safe_delete_from_storage(payload.cover_path)
            raise ReleaseNotFoundError

    async def _upload_to_storage(self, *, storage_key: str, temp_path: str) -> None:
        with Path(temp_path).open("rb") as stream:
            await self.storage.put(settings.minio_bucket, storage_key, stream)

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
