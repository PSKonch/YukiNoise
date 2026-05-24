from uuid import UUID

from yn.modules.artists.dto import ArtistDTO
from yn.modules.artists.errors import (
    ArtistAlreadyExistsError,
    ArtistDisplayedNameTakenError,
)
from yn.shared.unit_of_work import UnitOfWork


class ArtistService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_all_artists(self, *, limit: int, offset: int) -> list[ArtistDTO]:
        artists = await self.uow.artists.get_artists(limit=limit, offset=offset)
        return [ArtistDTO.from_orm(artist) for artist in artists]

    async def get_artist_by_user_id(self, user_id: UUID) -> ArtistDTO | None:
        artist = await self.uow.artists.get_artist_by_user_id(user_id)
        return ArtistDTO.from_orm(artist) if artist else None

    async def get_artist_by_id(self, artist_id: UUID) -> ArtistDTO | None:
        artist = await self.uow.artists.get_artist_by_id(artist_id)
        return ArtistDTO.from_orm(artist) if artist else None

    async def get_artist_by_displayed_name(
        self, displayed_name: str
    ) -> ArtistDTO | None:
        artist = await self.uow.artists.get_artist_by_displayed_name(displayed_name)
        return ArtistDTO.from_orm(artist) if artist else None

    async def full_text_search_artists(
        self,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> list[ArtistDTO]:
        artists = await self.uow.artists.full_text_search_artists(
            query,
            limit=limit,
            offset=offset,
        )

        if not artists:
            corrected_artists = (
                await self.uow.artists.trgm_search_artists_by_displayed_name(
                    query, limit=1, offset=0
                )
            )
            if corrected_artists:
                corrected_query = corrected_artists[0].displayed_name
                if corrected_query != query:
                    artists = await self.uow.artists.full_text_search_artists(
                        corrected_query,
                        limit=limit,
                        offset=offset,
                    )

        return [ArtistDTO.from_orm(artist) for artist in artists]

    async def create_artist(
        self,
        user_id: UUID,
        displayed_name: str,
        bio: str | None = None,
        social_links: dict[str, str] | None = None,
    ) -> ArtistDTO:
        existing_artist = await self.uow.artists.get_artist_by_user_id(user_id)
        if existing_artist is not None:
            raise ArtistAlreadyExistsError

        existing_name = await self.uow.artists.get_artist_by_displayed_name(
            displayed_name
        )
        if existing_name is not None:
            raise ArtistDisplayedNameTakenError

        artist = await self.uow.artists.create(
            user_id=user_id,
            displayed_name=displayed_name,
            bio=bio,
            social_links=social_links,
        )
        return ArtistDTO.from_orm(artist)

    async def update_artist(
        self,
        user_id: UUID,
        displayed_name: str | None = None,
        bio: str | None = None,
        social_links: dict[str, str] | None = None,
    ) -> bool:
        return await self.uow.artists.update(
            user_id=user_id,
            displayed_name=displayed_name,
            bio=bio,
            social_links=social_links,
        )

    async def hard_delete_artist(self, user_id: UUID) -> bool:
        return await self.uow.artists.hard_delete_artist(user_id)
