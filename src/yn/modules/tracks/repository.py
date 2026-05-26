from typing import TYPE_CHECKING, Sequence
from uuid import UUID

from sqlalchemy import and_, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from yn.modules.releases.model import Release
from yn.modules.tracks.errors import TrackConflictError
from yn.modules.tracks.model import Track

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
        except IntegrityError as exc:
            raise TrackConflictError from exc
        return result.scalar_one()
