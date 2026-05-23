from typing import TYPE_CHECKING, Sequence
from uuid import UUID

from sqlalchemy import and_, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from yn.modules.albums.model import Album
from yn.modules.tracks.errors import TrackConflictError
from yn.modules.tracks.model import Track

if TYPE_CHECKING:
    pass


class TrackRepository:
    model = Track

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        track_id: UUID,
        album_id: UUID,
        title: str,
        duration_seconds: int,
        path: str,
        genres: list[str],
    ) -> Track:
        stmt = (
            insert(self.model)
            .values(
                id=track_id,
                album_id=album_id,
                title=title,
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

    async def get_track_by_id(self, track_id: UUID) -> Track | None:
        stmt = (
            select(self.model)
            .join(self.model.album)
            .options(contains_eager(self.model.album))
            .where(
                and_(
                    self.model.id == track_id,
                    self.model.deleted_at.is_(None),
                    Album.public_visibility_clause(),
                )
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tracks(self, limit: int, offset: int) -> Sequence[Track]:
        stmt = (
            select(self.model)
            .join(self.model.album)
            .options(contains_eager(self.model.album))
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    Album.public_visibility_clause(),
                )
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_track_by_album_and_title(
        self, album_id: UUID, title: str
    ) -> Track | None:
        stmt = select(self.model).where(
            and_(
                self.model.album_id == album_id,
                func.lower(self.model.title) == title.lower(),
                self.model.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def trgm_search_by_title(self, search_term: str) -> Sequence[Track]:
        stmt = (
            select(self.model)
            .join(self.model.album)
            .options(contains_eager(self.model.album))
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    self.model.title.op("%")(search_term),
                    Album.public_visibility_clause(),
                )
            )
            .order_by(func.similarity(self.model.title, search_term).desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
