from yn.modules.users.model import User
from yn.modules.users.repository import UserRepository
from yn.modules.users.security import hash_password, verify_password


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await self.user_repository.get_user_by_id(user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.user_repository.get_user_by_email(email)

    async def is_email_taken(self, email: str) -> bool:
        return await self.user_repository.is_email_taken(email)

    async def create_user(self, email: str, password: str, role: str = "user") -> User:
        hashed_password = hash_password(password)
        user = await self.user_repository.create(
            email=email, hashed_password=hashed_password, role=role
        )
        await self.user_repository.session.commit()
        return user

    async def authenticate_user(self, email: str, password: str) -> User | None:
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def soft_delete_current_user(self, user_id: str) -> None:
        await self.user_repository.soft_delete_user(user_id)
        await self.user_repository.session.commit()

    async def restore_user(self, user_id: str) -> None:
        await self.user_repository.restore_user(user_id)
        await self.user_repository.session.commit()

    async def hard_delete_user(self, user_id: str) -> None:
        await self.user_repository.hard_delete_user(user_id)
        await self.user_repository.session.commit()

    async def update_user_email(self, user_id: str, new_email: str) -> None:
        await self.user_repository.update_email(user_id, new_email)
        await self.user_repository.session.commit()

    async def update_user_password(self, user_id: str, new_password: str) -> None:
        new_hashed_password = hash_password(new_password)
        await self.user_repository.update_password(user_id, new_hashed_password)
        await self.user_repository.session.commit()
