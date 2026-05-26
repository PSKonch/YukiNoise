from uuid import UUID

from sqlalchemy import and_, func, literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.playlists.errors import (
    PlaylistAccessDeniedError,
    PlaylistConflictError,
    PlaylistNotFoundError,
)
from yn.modules.playlists.model import Playlist, PlaylistTrack
from yn.modules.tracks.errors import TrackNotFoundError
from yn.modules.tracks.model import Track


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
        playlist_cte = (
            select(self.model.id, self.model.artist_id)
            .where(and_(self.model.id == playlist_id, self.model.deleted_at.is_(None)))
            .cte("playlist_cte")
        )
        track_cte = (
            select(Track.id)
            .where(and_(Track.id == track_id, Track.deleted_at.is_(None)))
            .cte("track_cte")
        )
        insert_cte = (
            pg_insert(self.auxiliary_model)
            .from_select(
                ["playlist_id", "track_id"],
                select(playlist_cte.c.id, track_cte.c.id).where(
                    playlist_cte.c.artist_id == profile_id
                ),
            )
            .on_conflict_do_nothing(index_elements=["playlist_id", "track_id"])
            .returning(literal(1).label("inserted"))
            .cte("insert_cte")
        )
        insert_count = select(func.count()).select_from(insert_cte).scalar_subquery()

        status_stmt = select(
            select(playlist_cte.c.id).scalar_subquery().label("playlist_id"),
            select(playlist_cte.c.artist_id)
            .scalar_subquery()
            .label("playlist_artist_id"),
            select(track_cte.c.id).scalar_subquery().label("track_id"),
            insert_count.label("inserted_count"),
        )

        status_result = await self._session.execute(status_stmt)
        status_row = status_result.one()
        if status_row.playlist_id is None:
            raise PlaylistNotFoundError
        if status_row.playlist_artist_id != profile_id:
            raise PlaylistAccessDeniedError
        if status_row.track_id is None:
            raise TrackNotFoundError
        if status_row.inserted_count == 0:
            raise PlaylistConflictError
