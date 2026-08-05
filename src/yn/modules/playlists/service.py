from typing import TYPE_CHECKING
from uuid import UUID

from yn.modules.playlists.dto import PlaylistDTO, PlaylistTrackDTO
from yn.modules.playlists.errors import (
    PlaylistAccessDeniedError,
    PlaylistNotFoundError,
    PlaylistTrackNotFoundError,
)
from yn.shared.unit_of_work import UnitOfWork

if TYPE_CHECKING:
    from yn.modules.playlists.model import Playlist


class PlaylistService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # Public read
    async def get_playlists(self, *, limit: int, offset: int) -> list[PlaylistDTO]:
        playlists = await self.uow.playlists.get_playlists(
            limit=limit,
            offset=offset,
        )
        return [PlaylistDTO.from_orm(playlist) for playlist in playlists]

    async def get_playlist_by_id(self, playlist_id: UUID) -> PlaylistDTO:
        playlist = await self.uow.playlists.get_public_playlist_by_id(playlist_id)
        if playlist is None:
            raise PlaylistNotFoundError
        return PlaylistDTO.from_orm(playlist)

    async def get_playlist_tracks(
        self, playlist_id: UUID, *, limit: int, offset: int
    ) -> list[PlaylistTrackDTO]:
        playlist = await self.uow.playlists.get_public_playlist_by_id(playlist_id)
        if playlist is None:
            raise PlaylistNotFoundError
        tracks = await self.uow.playlists.get_public_playlist_tracks(
            playlist_id=playlist_id,
            limit=limit,
            offset=offset,
        )
        return [PlaylistTrackDTO.from_orm(track) for track in tracks]

    # Owner read
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

    async def get_owned_playlist_by_id(
        self, playlist_id: UUID, artist_id: UUID
    ) -> PlaylistDTO:
        playlist = await self._get_owned_playlist_entity(
            playlist_id=playlist_id,
            artist_id=artist_id,
            include_deleted=True,
        )
        return PlaylistDTO.from_orm(playlist)

    async def get_owned_playlist_tracks(
        self, playlist_id: UUID, artist_id: UUID, *, limit: int, offset: int
    ) -> list[PlaylistTrackDTO]:
        await self._get_owned_playlist_entity(
            playlist_id=playlist_id,
            artist_id=artist_id,
            include_deleted=False,
        )
        tracks = await self.uow.playlists.get_playlist_tracks(
            playlist_id=playlist_id,
            limit=limit,
            offset=offset,
        )
        return [PlaylistTrackDTO.from_orm(track) for track in tracks]

    async def create_playlist(
        self,
        artist_id: UUID,
        title: str,
        description: str | None = None,
        cover_url: str | None = None,
        is_private: bool = False,
    ) -> PlaylistDTO:
        playlist = await self.uow.playlists.create(
            artist_id=artist_id,
            title=title,
            description=description,
            cover_url=cover_url,
            is_private=is_private,
        )
        await self.uow.commit()
        return PlaylistDTO.from_orm(playlist)

    async def create_favs_playlist(self, artist_id: UUID) -> None:
        await self.uow.playlists.create_system_favs(artist_id)
        await self.uow.commit()

    async def update_playlist(
        self,
        *,
        playlist_id: UUID,
        artist_id: UUID,
        title: str | None = None,
        description: str | None = None,
        cover_url: str | None = None,
        is_private: bool | None = None,
    ) -> PlaylistDTO:
        updated = await self.uow.playlists.update(
            playlist_id=playlist_id,
            artist_id=artist_id,
            title=title,
            description=description,
            cover_url=cover_url,
            is_private=is_private,
        )
        if updated is None:
            await self._raise_playlist_access_error(
                playlist_id=playlist_id,
                artist_id=artist_id,
                include_deleted=False,
            )
            raise PlaylistNotFoundError
        await self.uow.commit()
        return PlaylistDTO.from_orm(updated)

    async def delete_playlist(self, playlist_id: UUID, artist_id: UUID) -> None:
        deleted = await self.uow.playlists.soft_delete(
            playlist_id=playlist_id,
            artist_id=artist_id,
        )
        if not deleted:
            await self._raise_playlist_access_error(
                playlist_id=playlist_id,
                artist_id=artist_id,
                include_deleted=False,
            )
            raise PlaylistNotFoundError
        await self.uow.commit()

    async def add_track_to_playlist(
        self,
        playlist_id: UUID,
        track_id: UUID,
        artist_id: UUID,
    ) -> None:
        await self.uow.playlists.insert_track(
            playlist_id=playlist_id,
            track_id=track_id,
            profile_id=artist_id,
        )
        await self.uow.commit()

    async def remove_track_from_playlist(
        self,
        playlist_id: UUID,
        track_id: UUID,
        artist_id: UUID,
    ) -> None:
        await self._get_owned_playlist_entity(
            playlist_id=playlist_id,
            artist_id=artist_id,
            include_deleted=False,
        )
        removed = await self.uow.playlists.remove_track(
            playlist_id=playlist_id,
            track_id=track_id,
        )
        if not removed:
            raise PlaylistTrackNotFoundError
        await self.uow.commit()

    async def _get_owned_playlist_entity(
        self,
        *,
        playlist_id: UUID,
        artist_id: UUID,
        include_deleted: bool,
    ) -> "Playlist":
        playlist = await self.uow.playlists.get_playlist_by_id_including_deleted(
            playlist_id=playlist_id
        )
        if playlist is None:
            raise PlaylistNotFoundError
        if playlist.artist_id != artist_id:
            raise PlaylistAccessDeniedError
        if not include_deleted and playlist.deleted_at is not None:
            raise PlaylistNotFoundError
        return playlist

    async def _raise_playlist_access_error(
        self,
        *,
        playlist_id: UUID,
        artist_id: UUID,
        include_deleted: bool,
    ) -> None:
        await self._get_owned_playlist_entity(
            playlist_id=playlist_id,
            artist_id=artist_id,
            include_deleted=include_deleted,
        )
