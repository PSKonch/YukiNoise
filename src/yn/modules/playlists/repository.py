from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.tracks.errors import TrackNotFoundError
from yn.modules.tracks.model import Track

from .errors import (
    PlaylistAccessDeniedError,
    PlaylistConflictError,
)
from .model import Playlist, PlaylistTrack


class PlaylistsRepository:
    model = Playlist
    auxiliary_model = PlaylistTrack

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        artist_id: UUID,
        title: str,
        description: str | None = None,
        cover_url: str | None = None,
        is_private: bool = False,
    ) -> Playlist:
        stmt = (
            pg_insert(self.model)
            .values(
                artist_id=artist_id,
                title=title,
                description=description,
                cover_url=cover_url,
                is_private=is_private,
            )
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def insert_track(
        self,
        playlist_id: UUID,
        track_id: UUID,
        profile_id: UUID,
    ) -> None:
        playlist_query = select(self.model.id).where(
            and_(
                self.model.id == playlist_id,
                self.model.artist_id == profile_id,
                self.model.deleted_at.is_(None),
            )
        )
        playlist_result = await self._session.execute(playlist_query)
        owned_playlist_id = playlist_result.scalar_one_or_none()
        if owned_playlist_id is None:
            raise PlaylistAccessDeniedError

        track_query = select(Track.id).where(
            and_(Track.id == track_id, Track.deleted_at.is_(None))
        )
        track_result = await self._session.execute(track_query)
        existing_track_id = track_result.scalar_one_or_none()
        if existing_track_id is None:
            raise TrackNotFoundError

        stmt = (
            pg_insert(self.auxiliary_model)
            .values(playlist_id=playlist_id, track_id=track_id)
            .on_conflict_do_nothing(index_elements=["playlist_id", "track_id"])
            .returning(self.auxiliary_model)
        )
        result = await self._session.execute(stmt)
        inserted_row = result.scalar_one_or_none()
        if inserted_row is None:
            raise PlaylistConflictError
