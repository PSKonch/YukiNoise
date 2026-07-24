from typing import Annotated

from fastapi import Depends

from yn.modules.users.service import UserService
from yn.shared.unit_of_work import UnitOfWork, get_uow


def get_user_service(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> UserService:
    return UserService(uow)
