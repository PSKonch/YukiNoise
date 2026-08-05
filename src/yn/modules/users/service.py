from uuid import UUID

from yn.modules.auth.hasher import PasswordHasher
from yn.modules.users.dto import UserDTO
from yn.modules.users.errors import EmailAlreadyTakenError
from yn.shared.unit_of_work import UnitOfWork


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self._password_hasher = PasswordHasher()

    async def get_user_by_id(self, user_id: UUID) -> UserDTO | None:
        user = await self.uow.users.get_user_with_profile_by_id(user_id)
        return UserDTO.from_orm(user) if user else None

    async def get_user_by_email(self, email: str) -> UserDTO | None:
        user = await self.uow.users.get_user_with_profile_by_email(email)
        return UserDTO.from_orm(user) if user else None

    async def is_email_taken(self, email: str) -> bool:
        return await self.uow.users.is_email_taken(email)

    async def create_user(
        self, email: str, password: str, role: str = "user"
    ) -> UserDTO:
        hashed_password = self._password_hasher.hash_password(password)
        user = await self.uow.users.create(
            email=email, hashed_password=hashed_password, role=role
        )
        if user is None:
            raise EmailAlreadyTakenError
        await self.uow.commit()
        return UserDTO.from_orm(user)

    async def soft_delete_current_user(self, user_id: UUID) -> None:
        await self.uow.users.soft_delete_user(user_id)
        await self.uow.refresh_tokens.revoke_all_for_user(user_id)
        await self.uow.commit()

    async def restore_user(self, user_id: UUID) -> None:
        await self.uow.users.restore_user(user_id)
        await self.uow.commit()

    async def hard_delete_user(self, user_id: UUID) -> None:
        await self.uow.users.hard_delete_user(user_id)
        await self.uow.commit()

    async def update_user_email(self, user_id: UUID, new_email: str) -> None:
        await self.uow.users.update_email(user_id, new_email)
        await self.uow.commit()

    async def update_user_password(self, user_id: UUID, new_password: str) -> None:
        new_hashed_password = self._password_hasher.hash_password(new_password)
        await self.uow.users.update_password(user_id, new_hashed_password)
        await self.uow.commit()
