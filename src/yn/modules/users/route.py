from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from yn.modules.users.auth import get_current_user
from yn.modules.users.auth_service import AuthService
from yn.modules.users.deps import get_auth_service
from yn.modules.users.dto import UserDTO
from yn.modules.users.schemas import TokenPair, UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register")
async def register_user(
    payload: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    access_token, refresh_token = await auth_service.register(
        email=payload.email, password=payload.password
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/login")
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPair:
    access_token, refresh_token = await auth_service.login(
        form_data.username, form_data.password
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
):
    return UserRead.model_validate(current_user, from_attributes=True)


@router.delete("/me")
async def soft_delete_current_user(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth_service.soft_delete_user(current_user.id)
    return {"detail": "User soft deleted successfully"}


@router.post("/restore")
async def restore_current_user(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth_service.restore_user(current_user.id)
    return {"detail": "User restored successfully"}


@router.delete("/permanent")
async def hard_delete_current_user(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth_service.hard_delete_user(current_user.id)
    return {"detail": "User permanently deleted successfully"}
