from typing import Annotated

from fastapi import Depends

from yn.modules.commentaries.service import CommentaryService
from yn.shared.unit_of_work import UnitOfWork, get_read_uow, get_uow


def get_commentary_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> CommentaryService:
    return CommentaryService(uow)


def get_commentary_read_service(
    uow: Annotated[UnitOfWork, Depends(get_read_uow)],
) -> CommentaryService:
    return CommentaryService(uow)
