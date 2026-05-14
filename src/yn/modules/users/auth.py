from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

from yn.modules.users.deps import get_user_service
from yn.modules.users.dto import UserDTO
from yn.modules.users.service import UserService
from yn.shared.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserDTO:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except InvalidTokenError as exc:
        raise credentials_exception from exc

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user_uuid = UUID(str(user_id))
    except ValueError as exc:
        raise credentials_exception from exc

    user = await user_service.get_user_by_id(user_uuid)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise credentials_exception

    return user
