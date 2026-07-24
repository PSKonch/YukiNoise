from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from yn.modules.auth.hasher import PasswordHasher
from yn.modules.auth.security import SecurityManager
from yn.modules.auth.service import AuthService
from yn.modules.auth.token_processor import TokenProcessor
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork, get_uow


@lru_cache
def get_security_manager() -> SecurityManager:
    return SecurityManager(
        password_hasher=PasswordHasher(),
        token_processor=TokenProcessor(
            secret_key=settings.secret_key,
            algorithm=settings.algorithm,
            access_token_expire_minutes=settings.access_token_expire_minutes,
            refresh_token_expire_minutes=settings.refresh_token_expire_minutes,
        ),
    )


def get_auth_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    security: Annotated[SecurityManager, Depends(get_security_manager)],
) -> AuthService:
    return AuthService(uow=uow, security=security)
