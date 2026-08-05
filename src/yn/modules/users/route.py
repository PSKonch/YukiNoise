from typing import Annotated

from fastapi import APIRouter, Depends

from yn.modules.auth.auth import (
    get_current_user,
    get_current_user_allow_deleted,
)
from yn.modules.users.deps import get_user_service
from yn.modules.users.dto import UserDTO
from yn.modules.users.schemas import UserRead
from yn.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def read_current_user(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
) -> UserRead:
    return UserRead.model_validate(current_user, from_attributes=True)


@router.delete("/me")
async def soft_delete_current_user(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> dict[str, str]:
    await user_service.soft_delete_current_user(current_user.id)
    return {"detail": "User soft deleted successfully"}


@router.post("/restore")
async def restore_current_user(
    current_user: Annotated[UserDTO, Depends(get_current_user_allow_deleted)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> dict[str, str]:
    await user_service.restore_user(current_user.id)
    return {"detail": "User restored successfully"}


@router.delete("/permanent")
async def hard_delete_current_user(
    current_user: Annotated[UserDTO, Depends(get_current_user_allow_deleted)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> dict[str, str]:
    await user_service.hard_delete_user(current_user.id)
    return {"detail": "User permanently deleted successfully"}
