from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from yn.modules.auth.deps import get_auth_service
from yn.modules.auth.service import AuthService
from yn.modules.users.dto import UserDTO

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserDTO:
    return await auth_service.get_user_from_access_token(token)


async def get_current_user_allow_deleted(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserDTO:
    return await auth_service.get_user_from_access_token(token, allow_deleted=True)
