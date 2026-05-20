from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.tracks.model import Track


class TrackRepository:
    model = Track

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        album_id: UUID,
        title: str,
        duration_seconds: int,
        path: str,
        genres: list[str],
    ) -> Track:
        stmt = (
            insert(self.model)
            .values(
                album_id=album_id,
                title=title,
                duration_seconds=duration_seconds,
                path=path,
                genres=genres,
            )
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

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
