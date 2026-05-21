from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from yn.modules.albums.model import Album


class AlbumRepository:
    model = Album

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_album_by_id(self, album_id: UUID) -> Album | None:
        query = select(self.model).where(
            and_(self.model.id == album_id, self.model.deleted_at.is_(None))
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        profile_id: UUID,
        title: str,
        description: str | None,
        picture_path: str | None = None,
    ) -> Album:
        stmt = (
            insert(self.model)
            .values(
                profile_id=profile_id,
                title=title,
                description=description,
                picture_path=picture_path,
            )
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def update_picture_path(
        self,
        album_id: UUID,
        profile_id: UUID,
        picture_path: str | None,
    ) -> Album | None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == album_id,
                    self.model.profile_id == profile_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .values(picture_path=picture_path)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def trgm_search_by_title(
        self, search_term: str, limit: int, offset: int
    ) -> Sequence[Album]:
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    self.model.title.op("%")(search_term),
                )
            )
            .order_by(func.similarity(self.model.title, search_term).desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_albums(self, limit: int, offset: int) -> Sequence[Album]:
        query = (
            select(self.model)
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_albums_with_tracks_and_author_profile(
        self, limit: int, offset: int
    ) -> Sequence[Album]:
        query = (
            select(self.model)
            .options(
                joinedload(self.model.profile),
                selectinload(self.model.tracks),
            )
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().unique().all()
