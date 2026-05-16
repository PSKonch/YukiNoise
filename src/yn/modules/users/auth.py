from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

from yn.modules.users.deps import get_user_service
from yn.modules.users.dto import UserDTO
from yn.modules.users.errors import InvalidAuthCredentialsError
from yn.modules.users.service import UserService
from yn.shared.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserDTO:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except InvalidTokenError as exc:
        raise InvalidAuthCredentialsError from exc

    user_id = payload.get("sub")
    if user_id is None:
        raise InvalidAuthCredentialsError

    try:
        user_uuid = UUID(str(user_id))
    except ValueError as exc:
        raise InvalidAuthCredentialsError from exc

    user = await user_service.get_user_by_id(user_uuid)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise InvalidAuthCredentialsError

    return user
