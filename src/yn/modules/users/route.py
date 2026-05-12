from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.users.auth import create_access_token, create_refresh_token
from yn.modules.users.repository import UserRepository
from yn.modules.users.schemas import UserCreate
from yn.modules.users.service import UserService
from yn.shared.database import get_session

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(UserRepository(session))


@router.post("/register")
async def register_user(
    payload: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    existing_user = await user_service.user_repository.get_user_by_email(payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    user = await user_service.create_user(
        email=payload.email, password=payload.password
    )
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "refresh_token": refresh_token}
