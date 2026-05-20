from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.albums.model import Album
from yn.modules.profiles.model import Profile
from yn.modules.tracks.model import Track


class AlbumRepository:
    model = Album

    def __init__(self, session: AsyncSession):
        self._session = session

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

    async def trgm_search_by_title(self, search_term: str) -> Sequence[Album]:
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.deleted_at.is_(None),
                    self.model.title.op("%")(search_term),
                )
            )
            .order_by(func.similarity(self.model.title, search_term).desc())
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_albums(self) -> Sequence[Album]:
        query = (
            select(self.model)
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_albums_with_tracks_and_author_profile(self) -> Sequence[Album]:
        query = (
            select(
                self.model, Profile.displayed_name, Track.title, Track.duration_seconds
            )
            .join(Profile, self.model.profile_id == Profile.id)
            .join(Track, Track.album_id == self.model.id)
            .where(self.model.deleted_at.is_(None))
            .order_by(self.model.created_at.desc())
        )
        result = await self._session.execute(query)
        return result.scalars().all()
