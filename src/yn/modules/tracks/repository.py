from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.tracks.errors import TrackConflictError
from yn.modules.tracks.model import Track


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
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    self.model.title.op("%")(search_term),
                )
            )
            .order_by(func.similarity(self.model.title, search_term).desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_tracks(self) -> Sequence[Track]:
        stmt = (
            select(self.model)
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
