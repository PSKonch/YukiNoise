from typing import Tuple

from yn.modules.users.security import create_access_token, create_refresh_token
from yn.modules.users.service import UserService


class AuthService:
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    async def register(self, email: str, password: str) -> Tuple[str, str]:
        user = await self.user_service.create_user(email=email, password=password)
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        return access_token, refresh_token

    async def login(self, email: str, password: str) -> Tuple[str, str] | None:
        user = await self.user_service.authenticate_user(email, password)
        if user is None:
            return None
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        return access_token, refresh_token
