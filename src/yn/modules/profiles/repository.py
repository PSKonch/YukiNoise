from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import and_, delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from yn.modules.profiles.model import Profile


class ProfileRepository:
    model = Profile

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        user_id: UUID,
        displayed_name: str,
        bio: str | None = None,
        social_links: dict[str, str] | None = None,
    ) -> Profile:
        stmt = (
            insert(self.model)
            .values(
                user_id=user_id,
                displayed_name=displayed_name,
                bio=bio,
                social_links=social_links,
            )
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def update(
        self,
        user_id: UUID,
        displayed_name: str | None = None,
        bio: str | None = None,
        social_links: dict[str, str] | None = None,
    ) -> bool:
        values: dict[str, Any] = {}
        if displayed_name is not None:
            values["displayed_name"] = displayed_name
        if bio is not None:
            values["bio"] = bio
        if social_links is not None:
            values["social_links"] = social_links

        if not values:
            return False

        stmt = (
            update(self.model)
            .where(self.model.user_id == user_id)
            .values(**values)
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_profiles(self) -> Sequence[Profile]:
        query = (
            select(self.model)
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_profile_by_id(self, profile_id: UUID) -> Profile | None:
        query = select(self.model).where(self.model.id == profile_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_profile_by_user_id(self, user_id: UUID) -> Profile | None:
        query = select(self.model).where(self.model.user_id == user_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_profile_by_displayed_name(
        self, displayed_name: str
    ) -> Profile | None:
        query = select(self.model).where(self.model.displayed_name == displayed_name)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_profile_with_user_by_id(self, profile_id: UUID) -> Profile | None:
        query = (
            select(self.model)
            .options(selectinload(self.model.user))
            .where(self.model.id == profile_id)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def full_text_search_profiles(self, search: str) -> Sequence[Profile]:
        """
        Search profiles by displayed name and bio using full-text search
        """
        ts_query = func.websearch_to_tsquery("english", search)

        rank = func.ts_rank_cd(self.model.search_vector, ts_query)

        query = (
            select(self.model)
            .where(
                and_(
                    self.model.search_vector.op("@@")(ts_query),
                    self.model.deleted_at.is_(None),
                )
            )
            .order_by(rank.desc())
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def ilike_search_profiles(self, search: str) -> Sequence[Profile]:
        """
        Search profiles by displayed name and bio using ILIKE
        """
        pattern = f"%{search}%"
        query = select(self.model).where(
            and_(
                or_(
                    self.model.displayed_name.ilike(pattern),
                    self.model.bio.ilike(pattern),
                ),
                self.model.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def soft_delete_profile(self, user_id: UUID) -> bool:
        stmt = (
            update(self.model)
            .where(and_(self.model.user_id == user_id, self.model.deleted_at.is_(None)))
            .values(deleted_at=func.now())
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def restore_profile(self, user_id: UUID) -> bool:
        stmt = (
            update(self.model)
            .where(self.model.user_id == user_id)
            .values(deleted_at=None)
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def hard_delete_profile(self, user_id: UUID) -> bool:
        stmt = (
            delete(self.model)
            .where(self.model.user_id == user_id)
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
