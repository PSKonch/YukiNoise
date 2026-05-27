from uuid import UUID

from yn.modules.artists.dto import ArtistDTO
from yn.modules.artists.errors import (
    ArtistAlreadyExistsError,
    ArtistConflictError,
    ArtistDisplayedNameTakenError,
)
from yn.modules.playlists.dto import PlaylistDTO
from yn.modules.posts.dto import PostDTO
from yn.modules.releases.dto import ReleaseDTO
from yn.modules.tracks.dto import TrackDTO
from yn.shared.unit_of_work import UnitOfWork


class ArtistService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # Public read
    async def get_all_artists(self, *, limit: int, offset: int) -> list[ArtistDTO]:
        artists = await self.uow.artists.get_artists(limit=limit, offset=offset)
        return [ArtistDTO.from_orm(artist) for artist in artists]

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

    # Owner read
    async def get_artist_by_user_id(self, user_id: UUID) -> ArtistDTO | None:
        artist = await self.uow.artists.get_artist_by_user_id(user_id)
        return ArtistDTO.from_orm(artist) if artist else None

    async def get_artist_posts(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[PostDTO]:
        posts = await self.uow.posts.get_posts_by_artist_id(
            artist_id,
            limit=limit,
            offset=offset,
        )
        return [PostDTO.from_orm(post) for post in posts]

    async def get_artist_tracks(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[TrackDTO]:
        tracks = await self.uow.tracks.get_tracks_by_artist_id(
            artist_id,
            limit=limit,
            offset=offset,
        )
        return [TrackDTO.from_orm(track) for track in tracks]

    async def get_artist_playlists(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[PlaylistDTO]:
        playlists = await self.uow.playlists.get_public_playlists_by_artist_id(
            artist_id,
            limit=limit,
            offset=offset,
        )
        return [PlaylistDTO.from_orm(playlist) for playlist in playlists]

    async def get_artist_releases(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[ReleaseDTO]:
        releases = await self.uow.releases.get_public_releases_by_artist_id(
            artist_id,
            limit=limit,
            offset=offset,
        )
        return [ReleaseDTO.from_orm(release) for release in releases]

    # Owner read
    async def get_owned_posts(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[PostDTO]:
        return await self.get_artist_posts(
            artist_id,
            limit=limit,
            offset=offset,
        )

    async def get_owned_tracks(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[TrackDTO]:
        tracks = await self.uow.tracks.get_owned_tracks_by_artist_id(
            artist_id,
            limit=limit,
            offset=offset,
        )
        return [TrackDTO.from_orm(track) for track in tracks]

    async def get_owned_playlists(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[PlaylistDTO]:
        playlists = (
            await self.uow.playlists.get_playlists_by_artist_id_including_deleted(
                artist_id=artist_id,
                limit=limit,
                offset=offset,
            )
        )
        return [PlaylistDTO.from_orm(playlist) for playlist in playlists]

    async def get_owned_releases(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[ReleaseDTO]:
        releases = await self.uow.releases.get_owned_releases_including_deleted(
            artist_id=artist_id,
            limit=limit,
            offset=offset,
        )
        return [ReleaseDTO.from_orm(release) for release in releases]

    # Owner write
    async def create_artist(
        self,
        user_id: UUID,
        displayed_name: str,
        bio: str | None = None,
        social_links: dict[str, str] | None = None,
    ) -> ArtistDTO:
        try:
            artist = await self.uow.artists.create(
                user_id=user_id,
                displayed_name=displayed_name,
                bio=bio,
                social_links=social_links,
            )
        except ArtistConflictError as exc:
            user_taken, name_taken = await self.uow.artists.get_artist_conflict_flags(
                user_id=user_id,
                displayed_name=displayed_name,
            )
            if user_taken:
                raise ArtistAlreadyExistsError from exc
            if name_taken:
                raise ArtistDisplayedNameTakenError from exc
            raise

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
