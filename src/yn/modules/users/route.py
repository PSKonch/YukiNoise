from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from yn.modules.users.auth import (
    get_current_user,
    get_user_service,
)
from yn.modules.users.schemas import TokenPair, User, UserCreate, UserRead
from yn.modules.users.security import create_access_token, create_refresh_token
from yn.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register")
async def register_user(
    payload: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    if await user_service.is_email_taken(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    user = await user_service.create_user(
        email=payload.email, password=payload.password
    )
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/login")
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> TokenPair:
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user


@router.delete("/me")
async def soft_delete_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    await user_service.soft_delete_current_user(str(current_user.id))
    return {"detail": "User soft deleted successfully"}


@router.post("/restore")
async def restore_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    await user_service.restore_user(str(current_user.id))
    return {"detail": "User restored successfully"}


@router.delete("/permanent")
async def hard_delete_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    await user_service.hard_delete_user(str(current_user.id))
    return {"detail": "User permanently deleted successfully"}
