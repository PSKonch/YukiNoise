from typing import Annotated

from fastapi import Depends

from yn.modules.users.auth_service import AuthService
from yn.modules.users.service import UserService
from yn.shared.unit_of_work import UnitOfWork, get_uow


def get_user_service(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> UserService:
    return UserService(uow)


def get_auth_service(
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> AuthService:
    return AuthService(user_service)
