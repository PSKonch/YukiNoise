from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import and_, delete, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from yn.modules.artists.errors import ArtistConflictError
from yn.modules.artists.model import Artist


class ArtistRepository:
    model = Artist

    def __init__(self, session: AsyncSession):
        self._session = session

    # Public read
    async def get_artists(self, limit: int, offset: int) -> Sequence[Artist]:
        query = (
            select(self.model)
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_artist_by_id(self, artist_id: UUID) -> Artist | None:
        query = select(self.model).where(self.model.id == artist_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_artist_by_displayed_name(self, displayed_name: str) -> Artist | None:
        query = select(self.model).where(self.model.displayed_name == displayed_name)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_artist_conflict_flags(
        self, user_id: UUID, displayed_name: str
    ) -> tuple[bool, bool]:
        query = select(
            func.coalesce(func.bool_or(self.model.user_id == user_id), False).label(
                "user_taken"
            ),
            func.coalesce(
                func.bool_or(self.model.displayed_name == displayed_name), False
            ).label("name_taken"),
        ).where(
            or_(
                self.model.user_id == user_id,
                self.model.displayed_name == displayed_name,
            )
        )
        result = await self._session.execute(query)
        row = result.one()
        return bool(row.user_taken), bool(row.name_taken)

    async def full_text_search_artists(
        self, search: str, limit: int, offset: int
    ) -> Sequence[Artist]:
        ts_query_en = func.websearch_to_tsquery("english", search)
        ts_query_ru = func.websearch_to_tsquery("russian", search)

        rank = func.ts_rank_cd(self.model.search_vector, ts_query_en) + func.ts_rank_cd(
            self.model.search_vector, ts_query_ru
        )

        query = (
            select(self.model)
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

    async def trgm_search_artists_by_displayed_name(
        self, search_term: str, limit: int, offset: int
    ) -> Sequence[Artist]:
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    self.model.displayed_name.op("%")(search_term),
                )
            )
            .order_by(func.similarity(self.model.displayed_name, search_term).desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    # Owner read
    async def get_artist_by_user_id(self, user_id: UUID) -> Artist | None:
        query = select(self.model).where(self.model.user_id == user_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_artist_with_user_by_id(self, artist_id: UUID) -> Artist | None:
        query = (
            select(self.model)
            .options(selectinload(self.model.user))
            .where(self.model.id == artist_id)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    # Owner write
    async def create(
        self,
        user_id: UUID,
        displayed_name: str,
        bio: str | None = None,
        social_links: dict[str, str] | None = None,
    ) -> Artist:
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
        try:
            result = await self._session.execute(stmt)
        except IntegrityError as exc:
            raise ArtistConflictError from exc
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
        try:
            result = await self._session.execute(stmt)
        except IntegrityError as exc:
            raise ArtistConflictError from exc
        return result.scalar_one_or_none() is not None

    async def soft_delete_artist(self, user_id: UUID) -> bool:
        stmt = (
            update(self.model)
            .where(and_(self.model.user_id == user_id, self.model.deleted_at.is_(None)))
            .values(deleted_at=func.now())
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def restore_artist(self, user_id: UUID) -> bool:
        stmt = (
            update(self.model)
            .where(self.model.user_id == user_id)
            .values(deleted_at=None)
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def hard_delete_artist(self, user_id: UUID) -> bool:
        stmt = (
            delete(self.model)
            .where(self.model.user_id == user_id)
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
