from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import exists, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from yn.modules.artists.model import Artist
from yn.modules.follows.model import Follow
from yn.modules.notifications.enums import NotificationType
from yn.modules.notifications.model import Notification
from yn.modules.releases.model import Release
from yn.modules.users.model import User


@dataclass(frozen=True, slots=True)
class ReleaseNotificationSource:
    release_id: UUID
    artist_id: UUID
    title: str
    artist_name: str


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _visible_source() -> ColumnElement[bool]:
        return or_(
            Notification.release_id.is_(None),
            exists(
                select(Release.id)
                .join(Artist, Artist.id == Release.artist_id)
                .where(
                    Release.id == Notification.release_id,
                    Release.publicly_visible_clause(),
                    Artist.deleted_at.is_(None),
                )
            ),
        )

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
        unread_only: bool = False,
    ) -> Sequence[Notification]:
        query = select(Notification).where(
            Notification.user_id == user_id,
            self._visible_source(),
        )
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        result = await self._session.execute(
            query.order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def unread_count(self, user_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                self._visible_source(),
            )
        )
        return int(result.scalar_one())

    async def mark_read(
        self, user_id: UUID, notification_id: UUID
    ) -> Notification | None:
        result = await self._session.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(read_at=func.coalesce(Notification.read_at, func.now()))
            .returning(Notification)
        )
        return result.scalar_one_or_none()

    async def mark_all_read(self, user_id: UUID) -> int:
        result = await self._session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=func.now())
            .returning(Notification.id)
        )
        return len(result.scalars().all())

    async def get_release_source(
        self, release_id: UUID
    ) -> ReleaseNotificationSource | None:
        result = await self._session.execute(
            select(Release.id, Release.artist_id, Release.title, Artist.displayed_name)
            .join(Artist, Artist.id == Release.artist_id)
            .where(
                Release.id == release_id,
                Release.publicly_visible_clause(),
                Artist.deleted_at.is_(None),
            )
        )
        row = result.one_or_none()
        return ReleaseNotificationSource(*row) if row else None

    async def get_recipient_ids(
        self,
        artist_id: UUID,
        *,
        occurred_at: datetime,
        after: UUID | None = None,
        limit: int = 100,
    ) -> Sequence[UUID]:
        # The existing social graph belongs to artists, but notifications belong
        # to their user accounts. Don't notify people who followed after release.
        timestamp = occurred_at.astimezone(UTC).replace(tzinfo=None)
        query = (
            select(User.id)
            .join(Artist, Artist.user_id == User.id)
            .join(Follow, Follow.follower_id == Artist.id)
            .where(
                Follow.followed_id == artist_id,
                Follow.created_at <= timestamp,
                Artist.deleted_at.is_(None),
                User.deleted_at.is_(None),
                User.is_active,
            )
            .order_by(User.id)
            .limit(limit)
        )
        if after is not None:
            query = query.where(User.id > after)
        return (await self._session.execute(query)).scalars().all()

    async def add_release_notifications(
        self,
        source: ReleaseNotificationSource,
        user_ids: Sequence[UUID],
        *,
        occurred_at: datetime,
    ) -> None:
        if not user_ids:
            return
        timestamp = occurred_at.astimezone(UTC).replace(tzinfo=None)
        await self._session.execute(
            insert(Notification)
            .values(
                [
                    {
                        "user_id": user_id,
                        "release_id": source.release_id,
                        "type": NotificationType.NEW_RELEASE,
                        "title": "Новый релиз",
                        "message": f"{source.artist_name} — {source.title}",
                        "payload": {
                            "release_id": str(source.release_id),
                            "artist_id": str(source.artist_id),
                        },
                        "created_at": timestamp,
                    }
                    for user_id in user_ids
                ]
            )
            .on_conflict_do_nothing(constraint="uq_notifications_user_release")
        )
