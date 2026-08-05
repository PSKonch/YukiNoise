from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, delete, exists, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.artists.model import Artist
from yn.modules.follows.model import Follow


class FollowRepository:
    model = Follow

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_followers(
        self, followed_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Artist]:
        stmt = (
            select(Artist)
            .join(self.model, self.model.follower_id == Artist.id)
            .where(
                and_(
                    self.model.followed_id == followed_id,
                    Artist.deleted_at.is_(None),
                )
            )
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_following(
        self, follower_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Artist]:
        stmt = (
            select(Artist)
            .join(self.model, self.model.followed_id == Artist.id)
            .where(
                and_(
                    self.model.follower_id == follower_id,
                    Artist.deleted_at.is_(None),
                )
            )
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def is_following(self, follower_id: UUID, followed_id: UUID) -> bool:
        stmt = select(
            exists().where(
                and_(
                    self.model.follower_id == follower_id,
                    self.model.followed_id == followed_id,
                )
            )
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar_one())

    async def create(self, follower_id: UUID, followed_id: UUID) -> Follow | None:
        stmt = (
            pg_insert(self.model)
            .values(follower_id=follower_id, followed_id=followed_id)
            .on_conflict_do_nothing(
                constraint="uq_follower_followed",
            )
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, follower_id: UUID, followed_id: UUID) -> bool:
        stmt = (
            delete(self.model)
            .where(
                and_(
                    self.model.follower_id == follower_id,
                    self.model.followed_id == followed_id,
                )
            )
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
