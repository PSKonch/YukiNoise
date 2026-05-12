from yn.modules.users.auth import hash_password, verify_password
from yn.modules.users.repository import UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def create_user(self, email: str, password: str, role: str = "user"):
        hashed_password = hash_password(password)
        user = await self.user_repository.create(
            email=email, hashed_password=hashed_password, role=role
        )
        await self.user_repository.session.commit()
        return user

    async def authenticate_user(self, email: str, password: str):
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
