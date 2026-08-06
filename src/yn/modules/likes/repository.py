from uuid import UUID

from sqlalchemy import and_, delete, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.commentaries.model import Commentary
from yn.modules.likes.enums import TargetType
from yn.modules.likes.model import Like
from yn.modules.playlists.model import Playlist
from yn.modules.posts.model import Post
from yn.modules.releases.model import Release
from yn.modules.tracks.model import Track


class LikeRepository:
    model = Like

    def __init__(self, session: AsyncSession):
        self._session = session

    async def target_exists(self, target_type: TargetType, target_id: UUID) -> bool:
        if target_type == TargetType.TRACK:
            target_query = (
                select(Track.id)
                .join(Track.release)
                .where(
                    and_(
                        Track.id == target_id,
                        Track.deleted_at.is_(None),
                        Release.publicly_visible_clause(),
                    )
                )
            )
        elif target_type == TargetType.RELEASE:
            target_query = select(Release.id).where(
                and_(
                    Release.id == target_id,
                    Release.publicly_visible_clause(),
                )
            )
        elif target_type == TargetType.PLAYLIST:
            target_query = select(Playlist.id).where(
                and_(
                    Playlist.id == target_id,
                    Playlist.is_private.is_(False),
                    Playlist.deleted_at.is_(None),
                )
            )
        elif target_type == TargetType.POST:
            target_query = select(Post.id).where(
                and_(Post.id == target_id, Post.deleted_at.is_(None))
            )
        else:
            target_query = select(Commentary.id).where(
                and_(
                    Commentary.id == target_id,
                    Commentary.deleted_at.is_(None),
                )
            )

        result = await self._session.execute(select(exists(target_query)))
        return bool(result.scalar_one())

    async def is_liked(
        self, artist_id: UUID, target_type: TargetType, target_id: UUID
    ) -> bool:
        stmt = select(
            exists().where(
                and_(
                    self.model.artist_id == artist_id,
                    self.model.target_type == target_type,
                    self.model.target_id == target_id,
                )
            )
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar_one())

    async def create(
        self, artist_id: UUID, target_type: TargetType, target_id: UUID
    ) -> Like | None:
        stmt = (
            pg_insert(self.model)
            .values(
                artist_id=artist_id,
                target_type=target_type,
                target_id=target_id,
            )
            .on_conflict_do_nothing(constraint="uq_likes_artist_target")
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        like = result.scalar_one_or_none()
        if like is not None and target_type == TargetType.TRACK:
            await self._session.execute(
                update(Track)
                .where(Track.id == target_id)
                .values(like_count=Track.like_count + 1)
            )
        return like

    async def delete(
        self, artist_id: UUID, target_type: TargetType, target_id: UUID
    ) -> UUID | None:
        stmt = (
            delete(self.model)
            .where(
                and_(
                    self.model.artist_id == artist_id,
                    self.model.target_type == target_type,
                    self.model.target_id == target_id,
                )
            )
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        deleted_like_id = result.scalar_one_or_none()
        if deleted_like_id is not None and target_type == TargetType.TRACK:
            await self._session.execute(
                update(Track)
                .where(Track.id == target_id)
                .values(like_count=func.greatest(Track.like_count - 1, 0))
            )
        return deleted_like_id
