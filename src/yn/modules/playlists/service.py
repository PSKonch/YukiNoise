from uuid import UUID

from yn.modules.playlists.dto import PlaylistDTO
from yn.shared.unit_of_work import UnitOfWork


class PlaylistService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

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
        return PlaylistDTO.from_orm(playlist)

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
