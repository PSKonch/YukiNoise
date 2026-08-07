from typing import Annotated

from fastapi import Depends

from yn.modules.likes.service import LikeService
from yn.shared.outbox.publisher import OutboxPublisher, get_outbox_publisher
from yn.shared.unit_of_work import UnitOfWork, get_uow


def get_like_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    outbox_publisher: Annotated[OutboxPublisher, Depends(get_outbox_publisher)],
) -> LikeService:
    return LikeService(uow, outbox_publisher)
