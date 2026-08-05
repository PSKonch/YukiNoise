from typing import Annotated

from fastapi import Depends

from yn.modules.follows.service import FollowService
from yn.shared.unit_of_work import UnitOfWork, get_read_uow, get_uow


def get_follow_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> FollowService:
    return FollowService(uow)


def get_follow_read_service(
    uow: Annotated[UnitOfWork, Depends(get_read_uow)],
) -> FollowService:
    return FollowService(uow)
