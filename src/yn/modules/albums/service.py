from uuid import UUID

from sqlalchemy.exc import IntegrityError

from yn.modules.albums.dto import AlbumDTO
from yn.modules.albums.errors import AlbumConflictError
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

    async def get_albums(self) -> list[AlbumDTO]:
        albums = await self.uow.albums.get_albums()
        return [AlbumDTO.from_orm(album) for album in albums]

    async def trgm_search_by_title(self, search_term: str) -> list[AlbumDTO]:
        albums = await self.uow.albums.trgm_search_by_title(search_term)
        return [AlbumDTO.from_orm(album) for album in albums]
