from sqlalchemy import func, exists, or_, select, insert, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from yn.modules.profiles.model import Profile


class ProfileRepository:
    model = Profile

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
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
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update(
        self,
        profile_id: str,
        displayed_name: str | None = None,
        bio: str | None = None,
        social_links: dict[str, str] | None = None,
    ) -> None:
        values = {}
        if displayed_name is not None:
            values["displayed_name"] = displayed_name
        if bio is not None:
            values["bio"] = bio
        if social_links is not None:
            values["social_links"] = social_links

        stmt = update(self.model).where(self.model.id == profile_id).values(**values)
        await self.session.execute(stmt)

    async def get_profile_by_id(self, profile_id: str) -> Profile | None:
        query = select(self.model).where(self.model.id == profile_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_profile_with_user_by_id(self, profile_id: str) -> Profile | None:
        query = (
            select(self.model)
            .options(selectinload(self.model.user))
            .where(self.model.id == profile_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def full_text_search_profiles(self, search: str) -> list[Profile]:
        """
        Search profiles by displayed name and bio using full-text search
        """
        ts_query = func.plainto_tsquery("english", search)

        rank = func.ts_rank(self.model.search_vector, ts_query)

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
        result = await self.session.execute(query)
        return result.scalars().all()

    async def ilike_search_profiles(self, search: str) -> list[Profile]:
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
        result = await self.session.execute(query)
        return result.scalars().all()
