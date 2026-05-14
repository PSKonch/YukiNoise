from uuid import UUID

from yn.modules.users.security import create_access_token, create_refresh_token
from yn.modules.users.service import UserService


class AuthService:
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    async def register(self, email: str, password: str) -> tuple[str, str]:
        user = await self.user_service.create_user(email=email, password=password)
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        return access_token, refresh_token

    async def login(self, email: str, password: str) -> tuple[str, str] | None:
        user = await self.user_service.authenticate_user(email, password)
        if user is None:
            return None
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        return access_token, refresh_token

    async def is_email_taken(self, email: str) -> bool:
        return await self.user_service.is_email_taken(email)

    async def soft_delete_user(self, user_id: UUID) -> None:
        await self.user_service.soft_delete_current_user(user_id)

    async def restore_user(self, user_id: UUID) -> None:
        await self.user_service.restore_user(user_id)

    async def hard_delete_user(self, user_id: UUID) -> None:
        await self.user_service.hard_delete_user(user_id)
