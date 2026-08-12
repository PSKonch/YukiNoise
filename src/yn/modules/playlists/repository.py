from datetime import date
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import and_, case, delete, func, literal, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload
from sqlalchemy.sql.elements import ColumnElement

from yn.modules.playlists.enums import PlaylistType, SystemPlaylistKey
from yn.modules.playlists.errors import (
    PlaylistAccessDeniedError,
    PlaylistConflictError,
    PlaylistNotFoundError,
)
from yn.modules.playlists.model import Playlist, PlaylistTrack
from yn.modules.releases.model import Release
from yn.modules.tracks.errors import TrackNotFoundError
from yn.modules.tracks.model import Track


class PlaylistsRepository:
    model = Playlist
    auxiliary_model = PlaylistTrack

    def __init__(self, session: AsyncSession):
        self._session = session

    # Public read
    async def get_public_playlist_by_id(self, playlist_id: UUID) -> Playlist | None:
        stmt = select(self.model).where(
            and_(
                self.model.id == playlist_id,
                self.model.is_private.is_(False),
                self.model.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_public_playlists_by_artist_id(  # it's about other artist's playlists, so we need to filter out private ones
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Playlist]:
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.artist_id == artist_id,
                    self.model.is_private.is_(False),
                    self.model.deleted_at.is_(None),
                )
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_playlist_with_tracks_by_id(
        self, playlist_id: UUID
    ) -> Playlist | None:
        stmt = (
            select(self.model)
            .options(
                selectinload(self.model.tracks).selectinload(self.auxiliary_model.track)
            )
            .where(
                and_(
                    self.model.id == playlist_id,
                    self.model.is_private.is_(False),
                    self.model.deleted_at.is_(None),
                )
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_playlists(self, *, limit: int, offset: int) -> Sequence[Playlist]:
        chart_order = case(
            {
                SystemPlaylistKey.TOP_DAY.value: 0,
                SystemPlaylistKey.TOP_WEEK.value: 1,
                SystemPlaylistKey.TOP_MONTH.value: 2,
            },
            value=self.model.system_key,
            else_=3,
        )
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.is_private.is_(False),
                    self.model.deleted_at.is_(None),
                )
            )
            .order_by(chart_order.asc(), self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_public_playlist_tracks(
        self, playlist_id: UUID, *, limit: int, offset: int
    ) -> Sequence[PlaylistTrack]:
        stmt = (
            select(self.auxiliary_model)
            .join(self.auxiliary_model.playlist)
            .join(self.auxiliary_model.track)
            .join(Track.release)
            .options(contains_eager(self.auxiliary_model.track))
            .where(
                and_(
                    self.auxiliary_model.playlist_id == playlist_id,
                    self.model.is_private.is_(False),
                    self.model.deleted_at.is_(None),
                    Track.deleted_at.is_(None),
                    Release.publicly_visible_clause(),
                )
            )
            .order_by(
                self.auxiliary_model.position.asc(),
                self.auxiliary_model.added_at.asc(),
                self.auxiliary_model.track_id.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_accessible_playlist_tracks_for_playback(
        self, playlist_id: UUID, artist_id: UUID | None
    ) -> Sequence[Track]:
        access_clause: ColumnElement[bool] = self.model.is_private.is_(False)
        if artist_id is not None:
            access_clause = or_(access_clause, self.model.artist_id == artist_id)
        stmt = (
            select(Track)
            .join(self.auxiliary_model, self.auxiliary_model.track_id == Track.id)
            .join(self.model, self.model.id == self.auxiliary_model.playlist_id)
            .join(Track.release)
            .where(
                and_(
                    self.model.id == playlist_id,
                    self.model.deleted_at.is_(None),
                    access_clause,
                    Track.deleted_at.is_(None),
                    Release.publicly_visible_clause(),
                )
            )
            .order_by(
                self.auxiliary_model.position.asc(),
                self.auxiliary_model.added_at.asc(),
                Track.id.asc(),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # Owner read
    async def get_playlist_by_id_including_deleted(
        self, playlist_id: UUID
    ) -> Playlist | None:
        stmt = select(self.model).where(self.model.id == playlist_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_playlist_by_id(self, playlist_id: UUID) -> Playlist | None:
        stmt = select(self.model).where(
            and_(
                self.model.id == playlist_id,
                self.model.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_playlists_by_artist_id(  # it's about own playlists, so we can include private ones
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Playlist]:
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.artist_id == artist_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_playlists_by_artist_id_including_deleted(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Playlist]:
        stmt = (
            select(self.model)
            .where(self.model.artist_id == artist_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_playlist_tracks(
        self, playlist_id: UUID, *, limit: int, offset: int
    ) -> Sequence[PlaylistTrack]:
        stmt = (
            select(self.auxiliary_model)
            .join(self.auxiliary_model.track)
            .options(contains_eager(self.auxiliary_model.track))
            .where(
                and_(
                    self.auxiliary_model.playlist_id == playlist_id,
                    Track.deleted_at.is_(None),
                )
            )
            .order_by(
                self.auxiliary_model.position.asc(),
                self.auxiliary_model.added_at.asc(),
                self.auxiliary_model.track_id.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # Owner write
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

    async def create_system_favs(self, artist_id: UUID) -> None:
        stmt = (
            pg_insert(self.model)
            .values(
                artist_id=artist_id,
                title="favs",
                is_private=True,
                playlist_type=PlaylistType.SYSTEM,
            )
            .on_conflict_do_nothing(
                index_elements=[self.model.artist_id, self.model.title],
                index_where=text("playlist_type = 'SYSTEM'"),
            )
        )
        await self._session.execute(stmt)

    async def replace_system_chart(
        self,
        *,
        system_key: SystemPlaylistKey,
        title: str,
        description: str,
        period_start: date,
        period_end: date,
        track_ids: Sequence[UUID],
    ) -> None:
        insert_statement = pg_insert(self.model).values(
            artist_id=None,
            title=title,
            description=description,
            is_private=False,
            playlist_type=PlaylistType.SYSTEM,
            system_key=system_key.value,
            period_start=period_start,
            period_end=period_end,
        )
        playlist_statement = insert_statement.on_conflict_do_update(
            index_elements=[self.model.system_key],
            index_where=text("system_key IS NOT NULL"),
            set_={
                "title": insert_statement.excluded.title,
                "description": insert_statement.excluded.description,
                "is_private": False,
                "playlist_type": PlaylistType.SYSTEM,
                "period_start": insert_statement.excluded.period_start,
                "period_end": insert_statement.excluded.period_end,
                "deleted_at": None,
                "updated_at": func.now(),
            },
        ).returning(self.model.id)
        playlist_id = (await self._session.execute(playlist_statement)).scalar_one()

        await self._session.execute(
            delete(self.auxiliary_model).where(
                self.auxiliary_model.playlist_id == playlist_id
            )
        )
        if track_ids:
            await self._session.execute(
                pg_insert(self.auxiliary_model).values(
                    [
                        {
                            "playlist_id": playlist_id,
                            "track_id": track_id,
                            "position": position,
                        }
                        for position, track_id in enumerate(track_ids, start=1)
                    ]
                )
            )

    async def add_track_to_system_favs(
        self,
        artist_id: UUID,
        track_id: UUID,
    ) -> None:
        system_favs = select(
            self.model.id.label("playlist_id"),
            literal(track_id).label("track_id"),
        ).where(
            and_(
                self.model.artist_id == artist_id,
                self.model.title == "favs",
                self.model.playlist_type == PlaylistType.SYSTEM,
                self.model.deleted_at.is_(None),
            )
        )
        stmt = (
            pg_insert(self.auxiliary_model)
            .from_select(["playlist_id", "track_id"], system_favs)
            .on_conflict_do_nothing(index_elements=["playlist_id", "track_id"])
        )
        await self._session.execute(stmt)

    async def remove_track_from_system_favs(
        self,
        artist_id: UUID,
        track_id: UUID,
    ) -> None:
        system_favs_ids = select(self.model.id).where(
            and_(
                self.model.artist_id == artist_id,
                self.model.title == "favs",
                self.model.playlist_type == PlaylistType.SYSTEM,
            )
        )
        stmt = delete(self.auxiliary_model).where(
            and_(
                self.auxiliary_model.playlist_id.in_(system_favs_ids),
                self.auxiliary_model.track_id == track_id,
            )
        )
        await self._session.execute(stmt)

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

    async def remove_track(self, playlist_id: UUID, track_id: UUID) -> bool:
        track_stmt = select(Track.id).where(
            and_(Track.id == track_id, Track.deleted_at.is_(None))
        )
        track_result = await self._session.execute(track_stmt)
        if track_result.scalar_one_or_none() is None:
            raise TrackNotFoundError

        stmt = (
            delete(self.auxiliary_model)
            .where(
                and_(
                    self.auxiliary_model.playlist_id == playlist_id,
                    self.auxiliary_model.track_id == track_id,
                )
            )
            .returning(literal(1).label("deleted"))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update(
        self,
        playlist_id: UUID,
        artist_id: UUID,
        title: str | None = None,
        description: str | None = None,
        cover_url: str | None = None,
        is_private: bool | None = None,
    ) -> Playlist | None:
        values: dict[str, Any] = {}
        if title is not None:
            values["title"] = title
        if description is not None:
            values["description"] = description
        if cover_url is not None:
            values["cover_url"] = cover_url
        if is_private is not None:
            values["is_private"] = is_private

        if not values:
            return None

        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == playlist_id,
                    self.model.artist_id == artist_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .values(**values)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(self, playlist_id: UUID, artist_id: UUID) -> bool:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == playlist_id,
                    self.model.artist_id == artist_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .values(deleted_at=func.now())
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def hard_delete(self, playlist_id: UUID) -> bool:
        stmt = (
            delete(self.model)
            .where(self.model.id == playlist_id)
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
