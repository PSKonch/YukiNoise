from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from yn.modules.artists.model import Artist
from yn.modules.commentaries.model import Commentary
from yn.modules.posts.model import Post


class CommentaryRepository:
    model = Commentary

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_commentaries_by_post_id(
        self, post_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Commentary]:
        stmt = (
            select(self.model)
            .join(self.model.post)
            .join(self.model.artist)
            .options(
                selectinload(self.model.artist).load_only(
                    Artist.id, Artist.displayed_name
                )
            )
            .where(
                and_(
                    self.model.post_id == post_id,
                    self.model.deleted_at.is_(None),
                    Post.deleted_at.is_(None),
                    Artist.deleted_at.is_(None),
                )
            )
            .order_by(self.model.created_at.asc(), self.model.id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_commentary_by_id(self, commentary_id: UUID) -> Commentary | None:
        stmt = (
            select(self.model)
            .join(self.model.post)
            .join(self.model.artist)
            .options(
                selectinload(self.model.artist).load_only(
                    Artist.id, Artist.displayed_name
                )
            )
            .where(
                and_(
                    self.model.id == commentary_id,
                    self.model.deleted_at.is_(None),
                    Post.deleted_at.is_(None),
                    Artist.deleted_at.is_(None),
                )
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        artist_id: UUID,
        post_id: UUID,
        content: str,
        commentary_id: UUID | None = None,
    ) -> Commentary:
        stmt = (
            insert(self.model)
            .values(
                artist_id=artist_id,
                post_id=post_id,
                commentary_id=commentary_id,
                content=content,
            )
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def update(
        self, *, commentary_id: UUID, artist_id: UUID, content: str
    ) -> Commentary | None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == commentary_id,
                    self.model.artist_id == artist_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .values(content=content, updated_at=func.now())
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(self, *, commentary_id: UUID, artist_id: UUID) -> bool:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == commentary_id,
                    self.model.artist_id == artist_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .values(deleted_at=func.now())
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
