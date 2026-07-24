from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from yn.modules.auth.deps import get_auth_service
from yn.modules.auth.schemas import RefreshTokenRequest, RegisterRequest, TokenPair
from yn.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPair:
    token_pair = await auth_service.register(
        email=str(payload.email),
        password=payload.password,
    )
    return TokenPair.model_validate(token_pair, from_attributes=True)


@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPair:
    token_pair = await auth_service.login(
        email=form_data.username,
        password=form_data.password,
    )
    return TokenPair.model_validate(token_pair, from_attributes=True)


@router.post("/refresh")
async def refresh(
    payload: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPair:
    token_pair = await auth_service.refresh(payload.refresh_token)
    return TokenPair.model_validate(token_pair, from_attributes=True)


@router.post("/logout", status_code=204)
async def logout(
    payload: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    await auth_service.logout(payload.refresh_token)
