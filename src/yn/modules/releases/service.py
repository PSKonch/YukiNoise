from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from yn.modules.releases.dto import ReleaseDTO, ReleaseWithTracksAndAuthorDTO
from yn.modules.releases.enums import ReleaseStatus, ReleaseType
from yn.modules.releases.errors import (
    ReleaseAccessDeniedError,
    ReleaseCoverUploadFailedError,
    ReleaseNotDraftError,
    ReleaseNotFoundError,
    ReleaseNotScheduledError,
)
from yn.shared.minio import MinioStorage
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork


class ReleaseService:
    def __init__(self, uow: UnitOfWork, storage: MinioStorage):
        self.uow = uow
        self.storage = storage

    # Public read
    async def get_releases(self, *, limit: int, offset: int) -> list[ReleaseDTO]:
        releases = await self.uow.releases.get_releases(limit=limit, offset=offset)
        return [ReleaseDTO.from_orm(release) for release in releases]

    async def trgm_search_by_title(
        self, search_term: str, *, limit: int, offset: int
    ) -> list[ReleaseDTO]:
        releases = await self.uow.releases.trgm_search_by_title(
            search_term,
            limit=limit,
            offset=offset,
        )
        return [ReleaseDTO.from_orm(release) for release in releases]

    async def get_release_by_id(self, release_id: UUID) -> ReleaseDTO:
        release = await self.uow.releases.get_public_release_by_id(release_id)
        if release is None:
            raise ReleaseNotFoundError
        return ReleaseDTO.from_orm(release)

    async def get_releases_with_tracks_and_author_profile(
        self, *, limit: int, offset: int
    ) -> list[ReleaseWithTracksAndAuthorDTO]:
        releases = await self.uow.releases.get_releases_with_tracks_and_author_profile(
            limit=limit,
            offset=offset,
        )
        return [ReleaseWithTracksAndAuthorDTO.from_orm(release) for release in releases]

    async def get_release_with_tracks_and_author_profile_by_id(
        self, release_id: UUID
    ) -> ReleaseWithTracksAndAuthorDTO:
        release = (
            await self.uow.releases.get_release_with_tracks_and_author_profile_by_id(
                release_id=release_id
            )
        )
        if release is None:
            raise ReleaseNotFoundError
        return ReleaseWithTracksAndAuthorDTO.from_orm(release)

    # Owner read
    async def get_owned_releases(
        self,
        artist_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[ReleaseDTO]:
        releases = await self.uow.releases.get_owned_releases_including_deleted(
            artist_id=artist_id,
            limit=limit,
            offset=offset,
        )
        return [ReleaseDTO.from_orm(release) for release in releases]

    async def get_owned_release_by_id(
        self,
        release_id: UUID,
        artist_id: UUID,
    ) -> ReleaseDTO:
        release = await self.uow.releases.get_owned_release_by_id(
            release_id=release_id,
            artist_id=artist_id,
        )
        if release is None:
            raise ReleaseNotFoundError
        if release.artist_id != artist_id:
            raise ReleaseAccessDeniedError
        return ReleaseDTO.from_orm(release)

    async def get_owned_release_by_id_including_deleted(
        self,
        release_id: UUID,
        artist_id: UUID,
    ) -> ReleaseDTO:
        release = await self.uow.releases.get_owned_release_by_id_including_deleted(
            release_id=release_id,
            artist_id=artist_id,
        )
        if release is None:
            raise ReleaseNotFoundError
        if release.artist_id != artist_id:
            raise ReleaseAccessDeniedError
        return ReleaseDTO.from_orm(release)

    async def get_owned_draft_release_by_id(
        self,
        release_id: UUID,
        artist_id: UUID,
    ) -> ReleaseDTO:
        release = await self.uow.releases.get_release_by_id(release_id)
        if release is None:
            raise ReleaseNotFoundError
        if release.artist_id != artist_id:
            raise ReleaseAccessDeniedError
        if release.status != ReleaseStatus.DRAFT:
            raise ReleaseNotDraftError
        return ReleaseDTO.from_orm(release)

    async def get_owned_scheduled_release_by_id(
        self,
        release_id: UUID,
        artist_id: UUID,
    ) -> ReleaseDTO:
        release = await self.uow.releases.get_release_by_id(release_id)
        if release is None:
            raise ReleaseNotFoundError
        if release.artist_id != artist_id:
            raise ReleaseAccessDeniedError
        if release.status != ReleaseStatus.SCHEDULED:
            raise ReleaseNotScheduledError
        return ReleaseDTO.from_orm(release)

    # Owner write
    async def create_release(
        self,
        artist_id: UUID,
        title: str,
        description: str | None = None,
        cover_path: str | None = None,
        release_type: ReleaseType = ReleaseType.ALBUM,
    ) -> ReleaseDTO:
        release = await self.uow.releases.create(
            artist_id=artist_id,
            title=title,
            description=description,
            cover_path=cover_path,
            release_type=release_type,
        )
        return ReleaseDTO.from_orm(release)

    async def update_description_of_release(
        self,
        artist_id: UUID,
        release_id: UUID,
        description: str,
    ) -> ReleaseDTO:
        release = await self.uow.releases.get_release_by_id(release_id)
        if release is None:
            raise ReleaseNotFoundError
        if release.artist_id != artist_id:
            raise ReleaseAccessDeniedError
        if release.status != ReleaseStatus.DRAFT:
            raise ReleaseNotDraftError

        updated_release = await self.uow.releases.update_description(
            release_id=release_id,
            artist_id=artist_id,
            description=description,
        )
        if updated_release is None:
            raise ReleaseNotFoundError
        return ReleaseDTO.from_orm(updated_release)

    async def schedule_release(
        self,
        *,
        release_id: UUID,
        artist_id: UUID,
        release_date: datetime,
    ) -> ReleaseDTO:
        await self.get_owned_draft_release_by_id(
            release_id=release_id,
            artist_id=artist_id,
        )

        normalized_release_date = self._normalize_release_date(release_date)

        updated_release = await self.uow.releases.schedule_release(
            release_id=release_id,
            release_date=normalized_release_date,
        )
        if updated_release is None:
            raise ReleaseNotFoundError
        return ReleaseDTO.from_orm(updated_release)

    async def unschedule_release(
        self,
        *,
        release_id: UUID,
        artist_id: UUID,
    ) -> ReleaseDTO:
        await self.get_owned_scheduled_release_by_id(
            release_id=release_id,
            artist_id=artist_id,
        )

        updated_release = await self.uow.releases.unschedule_release(release_id)
        if updated_release is None:
            raise ReleaseNotFoundError
        return ReleaseDTO.from_orm(updated_release)

    async def upload_release_cover(
        self,
        *,
        release_id: UUID,
        artist_id: UUID,
        file: UploadFile,
    ) -> ReleaseDTO:
        release = await self.uow.releases.get_release_by_id(release_id)
        if release is None:
            raise ReleaseNotFoundError
        if release.artist_id != artist_id:
            raise ReleaseAccessDeniedError

        cover_path = self._build_cover_storage_key(
            release_id=release_id, filename=file.filename
        )
        await file.seek(0)

        try:
            await self.storage.put(settings.minio_bucket, cover_path, file.file)
            updated_release = await self.uow.releases.update_cover_path(
                release_id=release_id,
                artist_id=artist_id,
                cover_path=cover_path,
            )
        except Exception as exc:
            await self._safe_delete_cover(cover_path)
            raise ReleaseCoverUploadFailedError from exc

        if updated_release is None:
            await self._safe_delete_cover(cover_path)
            raise ReleaseNotFoundError

        return ReleaseDTO.from_orm(updated_release)

    def _build_cover_storage_key(
        self, *, release_id: UUID, filename: str | None
    ) -> str:
        suffix = Path(filename or "").suffix.lower()
        return f"releases/{release_id}/cover{suffix}"

    async def _safe_delete_cover(self, cover_path: str) -> None:
        try:
            await self.storage.delete(settings.minio_bucket, cover_path)
        except Exception:
            pass

    def _normalize_release_date(self, release_date: datetime) -> datetime:
        if release_date.tzinfo is None:
            return release_date
        return release_date.astimezone(UTC).replace(tzinfo=None)
