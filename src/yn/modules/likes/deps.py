from typing import Annotated

from fastapi import Depends

from yn.modules.likes.service import LikeService
from yn.shared.unit_of_work import UnitOfWork, get_uow


def get_like_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> LikeService:
    return LikeService(uow)
