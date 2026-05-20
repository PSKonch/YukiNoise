from uuid import UUID

from sqlalchemy.exc import IntegrityError

from yn.modules.albums.dto import AlbumDTO, AlbumWithTracksAndAuthorDTO
from yn.modules.albums.errors import (
    AlbumAccessDeniedError,
    AlbumConflictError,
    AlbumNotFoundError,
)
from yn.shared.unit_of_work import UnitOfWork


class AlbumService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_album(
        self,
        profile_id: UUID,
        title: str,
        description: str | None = None,
        picture_path: str | None = None,
    ) -> AlbumDTO:
        try:
            album = await self.uow.albums.create(
                profile_id=profile_id,
                title=title,
                description=description,
                picture_path=picture_path,
            )
        except IntegrityError as exc:
            raise AlbumConflictError from exc
        return AlbumDTO.from_orm(album)

    async def get_albums(self, *, limit: int, offset: int) -> list[AlbumDTO]:
        albums = await self.uow.albums.get_albums(limit=limit, offset=offset)
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
        album = await self.uow.albums.get_album_by_id(album_id)
        if album is None:
            raise AlbumNotFoundError
        if album.profile_id != profile_id:
            raise AlbumAccessDeniedError
        return AlbumDTO.from_orm(album)

    async def get_albums_with_tracks_and_author_profile(
        self, *, limit: int, offset: int
    ) -> list[AlbumWithTracksAndAuthorDTO]:
        albums = await self.uow.albums.get_albums_with_tracks_and_author_profile(
            limit=limit,
            offset=offset,
        )
        return [AlbumWithTracksAndAuthorDTO.from_orm(album) for album in albums]
