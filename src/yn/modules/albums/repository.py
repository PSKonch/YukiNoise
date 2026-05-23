from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from yn.modules.albums.errors import AlbumConflictError
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

    async def get_owned_album_by_id(
        self,
        album_id: UUID,
        profile_id: UUID,
    ) -> Album | None:
        query = select(self.model).where(
            and_(
                self.model.id == album_id,
                self.model.profile_id == profile_id,
                self.model.deleted_at.is_(None),
            )
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
                status="draft",
            )
            .returning(self.model)
        )
        try:
            result = await self._session.execute(stmt)
        except IntegrityError as exc:
            raise AlbumConflictError from exc
        return result.scalar_one()

    async def update_description(
        self,
        album_id: UUID,
        profile_id: UUID,
        description: str | None,
    ) -> Album | None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == album_id,
                    self.model.profile_id == profile_id,
                    self.model.deleted_at.is_(None),
                    self.model.status != "published",
                )
            )
            .values(description=description)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def release_album(self, album_id: UUID) -> Album | None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == album_id,
                    self.model.deleted_at.is_(None),
                    self.model.status == "scheduled",
                )
            )
            .values(status="published")
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def schedule_release_album(
        self, album_id: UUID, release_date: datetime
    ) -> Album | None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == album_id,
                    self.model.deleted_at.is_(None),
                    self.model.status == "draft",
                )
            )
            .values(status="scheduled", release_date=release_date)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def unschedule_release_album(self, album_id: UUID) -> Album | None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == album_id,
                    self.model.deleted_at.is_(None),
                    self.model.status == "scheduled",
                )
            )
            .values(status="draft", release_date=None)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_scheduled_albums_due_for_release(self) -> Sequence[Album]:
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    self.model.status == "scheduled",
                    self.model.release_date <= func.now(),
                )
            )
            .order_by(self.model.release_date.asc(), self.model.created_at.asc())
        )
        result = await self._session.execute(query)
        return result.scalars().all()

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
                    self.model.publicly_visible_clause(),
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
            .where(self.model.publicly_visible_clause())
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_owned_albums(
        self,
        profile_id: UUID,
        limit: int,
        offset: int,
    ) -> Sequence[Album]:
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    self.model.profile_id == profile_id,
                )
            )
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
            .where(self.model.publicly_visible_clause())
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().unique().all()

    async def get_album_with_tracks_and_author_profile_by_id(
        self, album_id: UUID
    ) -> Album | None:
        query = (
            select(self.model)
            .options(
                joinedload(self.model.profile),
                selectinload(self.model.tracks),
            )
            .where(
                and_(
                    self.model.id == album_id,
                    self.model.publicly_visible_clause(),
                )
            )
        )
        result = await self._session.execute(query)
        return result.scalars().first()
