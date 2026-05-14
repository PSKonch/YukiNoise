from uuid import UUID

from yn.modules.users.dto import UserDTO, from_orm
from yn.modules.users.security import hash_password, verify_password
from yn.shared.unit_of_work import UnitOfWork


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_user_by_id(self, user_id: UUID) -> UserDTO | None:
        user = await self.uow.users.get_user_by_id(user_id)
        return from_orm(user) if user else None

    async def get_user_by_email(self, email: str) -> UserDTO | None:
        user = await self.uow.users.get_user_by_email(email)
        return from_orm(user) if user else None

    async def is_email_taken(self, email: str) -> bool:
        return await self.uow.users.is_email_taken(email)

    async def create_user(
        self, email: str, password: str, role: str = "user"
    ) -> UserDTO:
        hashed_password = hash_password(password)
        user = await self.uow.users.create(
            email=email, hashed_password=hashed_password, role=role
        )
        return from_orm(user)

    async def authenticate_user(self, email: str, password: str) -> UserDTO | None:
        repo_user = await self.uow.users.get_user_by_email(email)
        if not repo_user:
            return None
        if not verify_password(password, repo_user.hashed_password):
            return None
        return from_orm(repo_user)

    async def soft_delete_current_user(self, user_id: UUID) -> None:
        await self.uow.users.soft_delete_user(user_id)

    async def restore_user(self, user_id: UUID) -> None:
        await self.uow.users.restore_user(user_id)

    async def hard_delete_user(self, user_id: UUID) -> None:
        await self.uow.users.hard_delete_user(user_id)

    async def update_user_email(self, user_id: UUID, new_email: str) -> None:
        await self.uow.users.update_email(user_id, new_email)

    async def update_user_password(self, user_id: UUID, new_password: str) -> None:
        new_hashed_password = hash_password(new_password)
        await self.uow.users.update_password(user_id, new_hashed_password)
