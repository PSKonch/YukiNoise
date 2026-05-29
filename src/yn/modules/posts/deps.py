from typing import Annotated

from fastapi import Depends

from yn.modules.posts.service import PostService
from yn.shared.unit_of_work import UnitOfWork, get_read_uow, get_uow


def get_post_service(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> PostService:
    return PostService(uow)


def get_post_read_service(
    uow: Annotated[UnitOfWork, Depends(get_read_uow)],
) -> PostService:
    return PostService(uow)
