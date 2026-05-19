from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import and_, delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from yn.modules.posts.model import Post
from yn.modules.profiles.model import Profile


class PostRepository:
    model = Post

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        profile_id: UUID,
        title: str,
        content: str,
    ) -> Post:
        stmt = (
            insert(self.model)
            .values(profile_id=profile_id, title=title, content=content)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def update(
        self,
        post_id: UUID,
        title: str | None = None,
        content: str | None = None,
    ) -> bool:
        values: dict[str, Any] = {}
        if title is not None:
            values["title"] = title
        if content is not None:
            values["content"] = content

        if not values:
            return False

        stmt = (
            update(self.model)
            .where(self.model.id == post_id)
            .values(**values)
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def hard_delete(self, post_id: UUID) -> bool:
        stmt = (
            delete(self.model).where(self.model.id == post_id).returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_posts_by_profile_id(self, profile_id: UUID) -> Sequence[Post]:
        query = (
            select(self.model)
            .options(
                selectinload(self.model.profile).load_only(
                    Profile.id, Profile.displayed_name
                )
            )
            .where(
                and_(
                    self.model.profile_id == profile_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .order_by(self.model.created_at.desc())
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_posts(self) -> Sequence[Post]:
        query = (
            select(self.model)
            .options(
                selectinload(self.model.profile).load_only(
                    Profile.id, Profile.displayed_name
                )
            )
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def full_text_search_posts(self, search: str) -> Sequence[Post]:
        """
        Search posts by title and content using full-text search
        """
        ts_query = func.websearch_to_tsquery("english", search)

        rank = func.ts_rank_cd(self.model.search_vector, ts_query)

        query = (
            select(self.model)
            .options(
                selectinload(self.model.profile).load_only(
                    Profile.id, Profile.displayed_name
                )
            )
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
