from typing import Annotated

from fastapi import Depends

from yn.modules.posts.service import PostService
from yn.shared.unit_of_work import UnitOfWork, get_uow


def get_post_service(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> PostService:
    return PostService(uow)
