from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import and_, delete, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from yn.modules.artists.model import Artist
from yn.modules.posts.errors import PostConflictError
from yn.modules.posts.model import Post


class PostRepository:
    model = Post

    def __init__(self, session: AsyncSession):
        self._session = session

    # Public read
    async def get_posts(self, limit: int, offset: int) -> Sequence[Post]:
        query = (
            select(self.model)
            .options(
                selectinload(self.model.artist).load_only(
                    Artist.id, Artist.displayed_name
                )
            )
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def full_text_search_posts(
        self, search: str, limit: int, offset: int
    ) -> Sequence[Post]:
        """
        Search posts by title and content using full-text search
        """
        ts_query_en = func.websearch_to_tsquery("english", search)
        ts_query_ru = func.websearch_to_tsquery("russian", search)

        rank = func.ts_rank_cd(self.model.search_vector, ts_query_en) + func.ts_rank_cd(
            self.model.search_vector, ts_query_ru
        )

        query = (
            select(self.model)
            .options(
                selectinload(self.model.artist).load_only(
                    Artist.id, Artist.displayed_name
                )
            )
            .where(
                and_(
                    or_(
                        self.model.search_vector.op("@@")(ts_query_en),
                        self.model.search_vector.op("@@")(ts_query_ru),
                    ),
                    self.model.deleted_at.is_(None),
                )
            )
            .order_by(rank.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    # Owner read
    async def get_posts_by_artist_id(
        self, artist_id: UUID, limit: int, offset: int
    ) -> Sequence[Post]:
        query = (
            select(self.model)
            .options(
                selectinload(self.model.artist).load_only(
                    Artist.id, Artist.displayed_name
                )
            )
            .where(
                and_(
                    self.model.artist_id == artist_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    # Owner write
    async def create(
        self,
        artist_id: UUID,
        title: str,
        content: str,
    ) -> Post:
        stmt = (
            insert(self.model)
            .values(artist_id=artist_id, title=title, content=content)
            .returning(self.model)
            .options(
                selectinload(self.model.artist).load_only(
                    Artist.id, Artist.displayed_name
                )
            )
        )
        try:
            result = await self._session.execute(stmt)
        except IntegrityError as exc:
            raise PostConflictError from exc
        return result.scalar_one()

    async def update(
        self,
        post_id: UUID,
        artist_id: UUID,
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
            .where(and_(self.model.id == post_id, self.model.artist_id == artist_id))
            .values(**values)
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def hard_delete(self, post_id: UUID, artist_id: UUID) -> bool:
        stmt = (
            delete(self.model)
            .where(and_(self.model.id == post_id, self.model.artist_id == artist_id))
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
