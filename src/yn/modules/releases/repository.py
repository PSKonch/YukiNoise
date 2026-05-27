from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from yn.modules.releases.enums import ReleaseStatus, ReleaseType
from yn.modules.releases.errors import ReleaseConflictError
from yn.modules.releases.model import Release


class ReleaseRepository:
    model = Release

    def __init__(self, session: AsyncSession):
        self._session = session

    # Public read
    async def get_public_release_by_id(self, release_id: UUID) -> Release | None:
        query = select(self.model).where(
            and_(self.model.id == release_id, self.model.publicly_visible_clause())
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def trgm_search_by_title(
        self, search_term: str, limit: int, offset: int
    ) -> Sequence[Release]:
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

    async def get_releases(self, limit: int, offset: int) -> Sequence[Release]:
        query = (
            select(self.model)
            .where(self.model.publicly_visible_clause())
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_public_releases_by_artist_id(
        self, artist_id: UUID, limit: int, offset: int
    ) -> Sequence[Release]:
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.artist_id == artist_id,
                    self.model.publicly_visible_clause(),
                )
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_releases_with_tracks_and_author_profile(
        self, limit: int, offset: int
    ) -> Sequence[Release]:
        query = (
            select(self.model)
            .options(
                joinedload(self.model.artist),
                selectinload(self.model.tracks),
            )
            .where(self.model.publicly_visible_clause())
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().unique().all()

    async def get_release_with_tracks_and_author_profile_by_id(
        self, release_id: UUID
    ) -> Release | None:
        query = (
            select(self.model)
            .options(
                joinedload(self.model.artist),
                selectinload(self.model.tracks),
            )
            .where(
                and_(
                    self.model.id == release_id,
                    self.model.publicly_visible_clause(),
                )
            )
        )
        result = await self._session.execute(query)
        return result.scalars().first()

    # Owner read
    async def get_release_by_id(self, release_id: UUID) -> Release | None:
        query = select(self.model).where(
            and_(self.model.id == release_id, self.model.deleted_at.is_(None))
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_owned_release_by_id(
        self,
        release_id: UUID,
        artist_id: UUID,
    ) -> Release | None:
        query = select(self.model).where(
            and_(
                self.model.id == release_id,
                self.model.artist_id == artist_id,
                self.model.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_owned_release_by_id_including_deleted(
        self,
        release_id: UUID,
        artist_id: UUID,
    ) -> Release | None:
        query = select(self.model).where(
            and_(
                self.model.id == release_id,
                self.model.artist_id == artist_id,
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_owned_releases(
        self,
        artist_id: UUID,
        limit: int,
        offset: int,
    ) -> Sequence[Release]:
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    self.model.artist_id == artist_id,
                )
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_owned_releases_including_deleted(
        self,
        artist_id: UUID,
        limit: int,
        offset: int,
    ) -> Sequence[Release]:
        query = (
            select(self.model)
            .where(self.model.artist_id == artist_id)
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
        description: str | None,
        cover_path: str | None = None,
        release_type: ReleaseType = ReleaseType.ALBUM,
    ) -> Release:
        stmt = (
            insert(self.model)
            .values(
                artist_id=artist_id,
                title=title,
                description=description,
                cover_path=cover_path,
                status=ReleaseStatus.DRAFT,
                release_type=release_type,
            )
            .returning(self.model)
        )
        try:
            result = await self._session.execute(stmt)
        except IntegrityError as exc:
            raise ReleaseConflictError from exc
        return result.scalar_one()

    async def update_description(
        self,
        release_id: UUID,
        artist_id: UUID,
        description: str | None,
    ) -> Release | None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == release_id,
                    self.model.artist_id == artist_id,
                    self.model.deleted_at.is_(None),
                    self.model.status == ReleaseStatus.DRAFT,
                )
            )
            .values(description=description)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_cover_path(
        self,
        release_id: UUID,
        artist_id: UUID,
        cover_path: str | None,
    ) -> Release | None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == release_id,
                    self.model.artist_id == artist_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .values(cover_path=cover_path)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def release_release(self, release_id: UUID) -> Release | None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == release_id,
                    self.model.deleted_at.is_(None),
                    self.model.status == ReleaseStatus.SCHEDULED,
                )
            )
            .values(status=ReleaseStatus.PUBLISHED)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def schedule_release(
        self, release_id: UUID, artist_id: UUID, release_date: datetime
    ) -> Release | None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == release_id,
                    self.model.artist_id == artist_id,
                    self.model.deleted_at.is_(None),
                    self.model.status == ReleaseStatus.DRAFT,
                )
            )
            .values(status=ReleaseStatus.SCHEDULED, release_date=release_date)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def unschedule_release(
        self, release_id: UUID, artist_id: UUID
    ) -> Release | None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == release_id,
                    self.model.artist_id == artist_id,
                    self.model.deleted_at.is_(None),
                    self.model.status == ReleaseStatus.SCHEDULED,
                )
            )
            .values(status=ReleaseStatus.DRAFT, release_date=None)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_scheduled_releases_due_for_release(self) -> Sequence[Release]:
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    self.model.status == ReleaseStatus.SCHEDULED,
                    self.model.release_date <= func.now(),
                )
            )
            .order_by(self.model.release_date.asc(), self.model.created_at.asc())
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def publish_due_releases(self) -> Sequence[UUID]:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    self.model.status == ReleaseStatus.SCHEDULED,
                    self.model.release_date <= func.now(),
                )
            )
            .values(status=ReleaseStatus.PUBLISHED)
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
