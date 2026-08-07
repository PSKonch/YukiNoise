from uuid import UUID

from yn.modules.likes.dto import LikeDTO
from yn.modules.likes.enums import TargetType
from yn.modules.likes.errors import (
    LikeAlreadyExistsError,
    LikeNotFoundError,
    LikeTargetNotFoundError,
)
from yn.modules.likes.events import (
    LIKES_EVENTS_TOPIC,
    LikeCreatedEvent,
    LikeDeletedEvent,
    like_target_key,
)
from yn.shared.outbox.publisher import OutboxPublisher
from yn.shared.unit_of_work import UnitOfWork


class LikeService:
    def __init__(self, uow: UnitOfWork, outbox_publisher: OutboxPublisher) -> None:
        self.uow = uow
        self.outbox_publisher = outbox_publisher

    async def is_liked(
        self, artist_id: UUID, target_type: TargetType, target_id: UUID
    ) -> bool:
        await self._ensure_target_exists(target_type, target_id)
        return await self.uow.likes.is_liked(
            artist_id=artist_id,
            target_type=target_type,
            target_id=target_id,
        )

    async def like(
        self, artist_id: UUID, target_type: TargetType, target_id: UUID
    ) -> LikeDTO:
        await self._ensure_target_exists(target_type, target_id)
        like = await self.uow.likes.create(
            artist_id=artist_id,
            target_type=target_type,
            target_id=target_id,
        )
        if like is None:
            raise LikeAlreadyExistsError

        like_dto = LikeDTO.from_orm(like)

        event = LikeCreatedEvent(
            like_id=like_dto.id,
            artist_id=like_dto.artist_id,
            target_type=like_dto.target_type,
            target_id=like_dto.target_id,
        )
        await self.uow.outbox.add(
            event_id=event.event_id,
            topic=LIKES_EVENTS_TOPIC,
            message_key=like_target_key(event.target_type, event.target_id),
            event_type=event.event_type,
            version=event.version,
            payload=event.model_dump(mode="json"),
        )
        await self.uow.commit()
        await self.outbox_publisher.publish_now(event.event_id)
        return like_dto

    async def unlike(
        self, artist_id: UUID, target_type: TargetType, target_id: UUID
    ) -> None:
        deleted_like_id = await self.uow.likes.delete(
            artist_id=artist_id,
            target_type=target_type,
            target_id=target_id,
        )
        if deleted_like_id is None:
            raise LikeNotFoundError

        event = LikeDeletedEvent(
            like_id=deleted_like_id,
            artist_id=artist_id,
            target_type=target_type,
            target_id=target_id,
        )
        await self.uow.outbox.add(
            event_id=event.event_id,
            topic=LIKES_EVENTS_TOPIC,
            message_key=like_target_key(event.target_type, event.target_id),
            event_type=event.event_type,
            version=event.version,
            payload=event.model_dump(mode="json"),
        )
        await self.uow.commit()
        await self.outbox_publisher.publish_now(event.event_id)

    async def _ensure_target_exists(
        self, target_type: TargetType, target_id: UUID
    ) -> None:
        if not await self.uow.likes.target_exists(target_type, target_id):
            raise LikeTargetNotFoundError
