from uuid import UUID

from yn.modules.likes.dto import LikeDTO
from yn.modules.likes.enums import TargetType
from yn.modules.likes.errors import (
    LikeAlreadyExistsError,
    LikeNotFoundError,
    LikeTargetNotFoundError,
)
from yn.modules.likes.events import LikeCreatedEvent, LikeDeletedEvent
from yn.shared.publisher.kafka_pub import KafkaPublisher
from yn.shared.unit_of_work import UnitOfWork


class LikeService:
    def __init__(self, uow: UnitOfWork, kafka_publisher: KafkaPublisher) -> None:
        self.uow = uow
        self.kafka_publisher = kafka_publisher

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
        await self.uow.commit()

        like_dto = LikeDTO.from_orm(like)

        event = LikeCreatedEvent(
            like_id=like_dto.id,
            artist_id=like_dto.artist_id,
            target_type=like_dto.target_type,
            target_id=like_dto.target_id,
        )
        await self.kafka_publisher.publish(
            message=event,
            key=event.artist_id,
            headers={
                "event-type": event.event_type,
                "event-version": str(event.version),
            },
            correlation_id=str(event.event_id),
        )
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
        await self.uow.commit()

        event = LikeDeletedEvent(
            like_id=deleted_like_id,
            artist_id=artist_id,
            target_type=target_type,
            target_id=target_id,
        )
        await self.kafka_publisher.publish(
            message=event,
            key=event.artist_id,
            headers={
                "event-type": event.event_type,
                "event-version": str(event.version),
            },
            correlation_id=str(event.event_id),
        )

    async def _ensure_target_exists(
        self, target_type: TargetType, target_id: UUID
    ) -> None:
        if not await self.uow.likes.target_exists(target_type, target_id):
            raise LikeTargetNotFoundError
