from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from yn.modules.albums.dto import AlbumDTO, AlbumWithTracksAndAuthorDTO
from yn.modules.albums.errors import (
    AlbumAccessDeniedError,
    AlbumNotDraftError,
    AlbumNotFoundError,
    AlbumNotScheduledError,
    AlbumPictureUploadFailedError,
)
from yn.shared.minio import MinioStorage
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork


class AlbumService:
    def __init__(self, uow: UnitOfWork, storage: MinioStorage):
        self.uow = uow
        self.storage = storage

    async def create_album(
        self,
        profile_id: UUID,
        title: str,
        description: str | None = None,
        picture_path: str | None = None,
    ) -> AlbumDTO:
        album = await self.uow.albums.create(
            profile_id=profile_id,
            title=title,
            description=description,
            picture_path=picture_path,
        )
        return AlbumDTO.from_orm(album)

    async def update_description_of_album(
        self,
        profile_id: UUID,
        album_id: UUID,
        description: str,
    ) -> AlbumDTO:
        album = await self.uow.albums.update_description(
            album_id=album_id,
            profile_id=profile_id,
            description=description,
        )
        if album is None:
            raise AlbumNotFoundError
        if album.profile_id != profile_id:
            raise AlbumAccessDeniedError
        if album.status != "draft":
            raise AlbumNotDraftError
        return AlbumDTO.from_orm(album)

    async def get_albums(self, *, limit: int, offset: int) -> list[AlbumDTO]:
        albums = await self.uow.albums.get_albums(limit=limit, offset=offset)
        return [AlbumDTO.from_orm(album) for album in albums]

    async def get_owned_albums(
        self,
        profile_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[AlbumDTO]:
        albums = await self.uow.albums.get_owned_albums(
            profile_id=profile_id,
            limit=limit,
            offset=offset,
        )
        return [AlbumDTO.from_orm(album) for album in albums]

    async def trgm_search_by_title(
        self, search_term: str, *, limit: int, offset: int
    ) -> list[AlbumDTO]:
        albums = await self.uow.albums.trgm_search_by_title(
            search_term,
            limit=limit,
            offset=offset,
        )
        return [AlbumDTO.from_orm(album) for album in albums]

    async def get_album_by_id(self, album_id: UUID) -> AlbumDTO:
        album = await self.uow.albums.get_album_by_id(album_id)
        if album is None:
            raise AlbumNotFoundError
        return AlbumDTO.from_orm(album)

    async def get_owned_album_by_id(
        self,
        album_id: UUID,
        profile_id: UUID,
    ) -> AlbumDTO:
        album = await self.uow.albums.get_owned_album_by_id(
            album_id=album_id,
            profile_id=profile_id,
        )
        if album is None:
            raise AlbumNotFoundError
        if album.profile_id != profile_id:
            raise AlbumAccessDeniedError
        return AlbumDTO.from_orm(album)

    async def get_owned_draft_album_by_id(
        self,
        album_id: UUID,
        profile_id: UUID,
    ) -> AlbumDTO:
        album = await self.uow.albums.get_album_by_id(album_id)
        if album is None:
            raise AlbumNotFoundError
        if album.profile_id != profile_id:
            raise AlbumAccessDeniedError
        if album.status != "draft":
            raise AlbumNotDraftError
        return AlbumDTO.from_orm(album)

    async def get_owned_scheduled_album_by_id(
        self,
        album_id: UUID,
        profile_id: UUID,
    ) -> AlbumDTO:
        album = await self.uow.albums.get_album_by_id(album_id)
        if album is None:
            raise AlbumNotFoundError
        if album.profile_id != profile_id:
            raise AlbumAccessDeniedError
        if album.status != "scheduled":
            raise AlbumNotScheduledError
        return AlbumDTO.from_orm(album)

    async def schedule_album_release(
        self,
        *,
        album_id: UUID,
        profile_id: UUID,
        release_date: datetime,
    ) -> AlbumDTO:
        await self.get_owned_draft_album_by_id(
            album_id=album_id,
            profile_id=profile_id,
        )

        normalized_release_date = self._normalize_release_date(release_date)

        updated_album = await self.uow.albums.schedule_release_album(
            album_id=album_id,
            release_date=normalized_release_date,
        )
        if updated_album is None:
            raise AlbumNotFoundError
        return AlbumDTO.from_orm(updated_album)

    async def unschedule_album_release(
        self,
        *,
        album_id: UUID,
        profile_id: UUID,
    ) -> AlbumDTO:
        await self.get_owned_scheduled_album_by_id(
            album_id=album_id,
            profile_id=profile_id,
        )

        updated_album = await self.uow.albums.unschedule_release_album(album_id)
        if updated_album is None:
            raise AlbumNotFoundError
        return AlbumDTO.from_orm(updated_album)

    async def get_albums_with_tracks_and_author_profile(
        self, *, limit: int, offset: int
    ) -> list[AlbumWithTracksAndAuthorDTO]:
        albums = await self.uow.albums.get_albums_with_tracks_and_author_profile(
            limit=limit,
            offset=offset,
        )
        return [AlbumWithTracksAndAuthorDTO.from_orm(album) for album in albums]

    async def get_album_with_tracks_and_author_profile_by_id(
        self, album_id: UUID
    ) -> AlbumWithTracksAndAuthorDTO:
        album = await self.uow.albums.get_album_with_tracks_and_author_profile_by_id(
            album_id=album_id
        )
        if album is None:
            raise AlbumNotFoundError
        return AlbumWithTracksAndAuthorDTO.from_orm(album)

    async def upload_album_picture(
        self,
        *,
        album_id: UUID,
        profile_id: UUID,
        file: UploadFile,
    ) -> AlbumDTO:
        album = await self.uow.albums.get_album_by_id(album_id)
        if album is None:
            raise AlbumNotFoundError
        if album.profile_id != profile_id:
            raise AlbumAccessDeniedError

        picture_path = self._build_picture_storage_key(
            album_id=album_id, filename=file.filename
        )
        await file.seek(0)

        try:
            await self.storage.put(settings.minio_bucket, picture_path, file.file)
            updated_album = await self.uow.albums.update_picture_path(
                album_id=album_id,
                profile_id=profile_id,
                picture_path=picture_path,
            )
        except Exception as exc:
            await self._safe_delete_picture(picture_path)
            raise AlbumPictureUploadFailedError from exc

        if updated_album is None:
            await self._safe_delete_picture(picture_path)
            raise AlbumNotFoundError

        return AlbumDTO.from_orm(updated_album)

    def _build_picture_storage_key(
        self, *, album_id: UUID, filename: str | None
    ) -> str:
        suffix = Path(filename or "").suffix.lower()
        return f"albums/{album_id}/cover{suffix}"

    async def _safe_delete_picture(self, picture_path: str) -> None:
        try:
            await self.storage.delete(settings.minio_bucket, picture_path)
        except Exception:
            pass

    def _normalize_release_date(self, release_date: datetime) -> datetime:
        if release_date.tzinfo is None:
            return release_date
        return release_date.astimezone(UTC).replace(tzinfo=None)
