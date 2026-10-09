from typing import TYPE_CHECKING, Any, Sequence
from uuid import UUID

from sqlalchemy import and_, delete, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from yn.modules.artists.model import Artist
from yn.modules.likes.enums import TargetType
from yn.modules.likes.model import Like
from yn.modules.releases.model import Release
from yn.modules.tracks.errors import TrackConflictError
from yn.modules.tracks.model import Track, TrackFeature

if TYPE_CHECKING:
    pass


class TrackRepository:
    model = Track

    def __init__(self, session: AsyncSession):
        self._session = session

    # Public read
    async def get_track_by_id(self, track_id: UUID) -> Track | None:
        stmt = (
            select(self.model)
            .join(self.model.release)
            .options(contains_eager(self.model.release))
            .where(
                and_(
                    self.model.id == track_id,
                    self.model.deleted_at.is_(None),
                    Release.publicly_visible_clause(),
                )
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tracks(self, limit: int, offset: int) -> Sequence[Track]:
        stmt = (
            select(self.model)
            .join(self.model.release)
            .options(contains_eager(self.model.release))
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    Release.publicly_visible_clause(),
                )
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_public_tracks_for_release(self, release_id: UUID) -> Sequence[Track]:
        stmt = (
            select(self.model)
            .join(self.model.release)
            .where(
                and_(
                    self.model.release_id == release_id,
                    self.model.deleted_at.is_(None),
                    Release.publicly_visible_clause(),
                )
            )
            .order_by(self.model.track_number_in_release.asc(), self.model.id.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def increment_play_count(self, track_id: UUID) -> bool:
        stmt = (
            update(self.model)
            .where(and_(self.model.id == track_id, self.model.deleted_at.is_(None)))
            .values(play_count=self.model.play_count + 1)
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def sync_like_count(self, track_id: UUID) -> bool:
        like_count = (
            select(func.count(Like.id))
            .where(
                and_(
                    Like.target_type == TargetType.TRACK,
                    Like.target_id == track_id,
                )
            )
            .scalar_subquery()
        )
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == track_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .values(like_count=like_count)
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def trgm_search_by_title(self, search_term: str) -> Sequence[Track]:
        stmt = (
            select(self.model)
            .join(self.model.release)
            .options(contains_eager(self.model.release))
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    self.model.title.op("%")(search_term),
                    Release.publicly_visible_clause(),
                )
            )
            .order_by(func.similarity(self.model.title, search_term).desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_tracks_by_artist_id(
        self, artist_id: UUID, limit: int, offset: int
    ) -> Sequence[Track]:
        stmt = (
            select(self.model)
            .join(self.model.release)
            .options(contains_eager(self.model.release))
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    or_(
                        Release.artist_id == artist_id,
                        self.model.featured_artists.any(
                            and_(Artist.id == artist_id, Artist.deleted_at.is_(None))
                        ),
                    ),
                    Release.publicly_visible_clause(),
                )
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # Owner read
    async def get_track_by_release_and_title(
        self, release_id: UUID, title: str
    ) -> Track | None:
        stmt = select(self.model).where(
            and_(
                self.model.release_id == release_id,
                func.lower(self.model.title) == title.lower(),
                self.model.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_track_by_release_and_number(
        self, release_id: UUID, track_number_in_release: int
    ) -> Track | None:
        stmt = select(self.model).where(
            and_(
                self.model.release_id == release_id,
                self.model.track_number_in_release == track_number_in_release,
                self.model.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_owned_tracks_by_artist_id(
        self, artist_id: UUID, limit: int, offset: int
    ) -> Sequence[Track]:
        stmt = (
            select(self.model)
            .join(self.model.release)
            .options(contains_eager(self.model.release))
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    Release.artist_id == artist_id,
                    Release.deleted_at.is_(None),
                )
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_track_by_id_for_artist(
        self, track_id: UUID, artist_id: UUID
    ) -> Track | None:
        stmt = (
            select(self.model)
            .join(self.model.release)
            .options(contains_eager(self.model.release))
            .where(
                and_(
                    self.model.id == track_id,
                    self.model.deleted_at.is_(None),
                    Release.artist_id == artist_id,
                    Release.deleted_at.is_(None),
                )
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_conflicting_track_for_release(
        self,
        release_id: UUID,
        title: str,
        track_number_in_release: int,
    ) -> Track | None:
        normalized_title = title.lower()
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.release_id == release_id,
                    self.model.deleted_at.is_(None),
                    or_(
                        func.lower(self.model.title) == normalized_title,
                        self.model.track_number_in_release == track_number_in_release,
                    ),
                )
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    # Owner write
    async def create(
        self,
        track_id: UUID,
        release_id: UUID,
        title: str,
        track_number_in_release: int,
        duration_seconds: int,
        path: str,
        genres: list[str],
        featured_artist_ids: list[UUID] | None = None,
    ) -> Track:
        stmt = (
            insert(self.model)
            .values(
                id=track_id,
                release_id=release_id,
                title=title,
                track_number_in_release=track_number_in_release,
                duration_seconds=duration_seconds,
                path=path,
                genres=genres,
            )
            .returning(self.model)
        )
        try:
            result = await self._session.execute(stmt)
            track = result.scalar_one()
            await self._replace_featured_artists(track, featured_artist_ids or [])
        except IntegrityError as exc:
            raise TrackConflictError from exc
        return track

    async def update(
        self,
        *,
        track_id: UUID,
        release_id: UUID,
        title: str | None = None,
        track_number_in_release: int | None = None,
        genres: list[str] | None = None,
        featured_artist_ids: list[UUID] | None = None,
    ) -> Track | None:
        values: dict[str, Any] = {}
        if title is not None:
            values["title"] = title
        if track_number_in_release is not None:
            values["track_number_in_release"] = track_number_in_release
        if genres is not None:
            values["genres"] = genres

        if not values and featured_artist_ids is None:
            return None

        clause = and_(
            self.model.id == track_id,
            self.model.release_id == release_id,
            self.model.deleted_at.is_(None),
        )
        stmt = (
            update(self.model).where(clause).values(**values).returning(self.model)
            if values
            else select(self.model).where(clause).with_for_update()
        )
        try:
            result = await self._session.execute(stmt)
            track = result.scalar_one_or_none()
            if track is not None and featured_artist_ids is not None:
                await self._replace_featured_artists(track, featured_artist_ids)
        except IntegrityError as exc:
            raise TrackConflictError from exc
        return track

    async def _replace_featured_artists(
        self, track: Track, featured_artist_ids: list[UUID]
    ) -> None:
        await self._session.execute(
            delete(TrackFeature).where(TrackFeature.track_id == track.id)
        )
        if featured_artist_ids:
            await self._session.execute(
                insert(TrackFeature).values(
                    [
                        {"track_id": track.id, "artist_id": artist_id}
                        for artist_id in featured_artist_ids
                    ]
                )
            )
        await self._session.refresh(track, ["featured_artists"])

    async def soft_delete(self, track_id: UUID, release_id: UUID) -> bool:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == track_id,
                    self.model.release_id == release_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .values(deleted_at=func.now())
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
