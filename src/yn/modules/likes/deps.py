from typing import Annotated

from fastapi import Depends

from yn.modules.likes.events import LIKES_EVENTS_TOPIC
from yn.modules.likes.service import LikeService
from yn.shared.publisher.kafka_pub import KafkaPublisher, get_kafka_publisher
from yn.shared.unit_of_work import UnitOfWork, get_uow


def get_like_events_publisher() -> KafkaPublisher:
    return get_kafka_publisher(LIKES_EVENTS_TOPIC)


def get_like_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    kafka_publisher: Annotated[KafkaPublisher, Depends(get_like_events_publisher)],
) -> LikeService:
    return LikeService(uow, kafka_publisher)
