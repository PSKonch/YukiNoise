from sqlalchemy import func, exists, select, insert, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from yn.modules.users.model import User


class UserRepository:
    model = User

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, email: str, hashed_password: str) -> User:
        stmt = (
            insert(self.model)
            .values(
                email=email,
                hashed_password=hashed_password,
            )
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_password(self, user_id: str, new_hashed_password: str) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == user_id)
            .values(hashed_password=new_hashed_password)
        )
        await self.session.execute(stmt)

    async def get_user_by_id(self, user_id: str) -> User | None:
        query = select(self.model).where(self.model.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        query = select(self.model).where(self.model.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_with_profile_by_id(self, user_id: str) -> User | None:
        query = (
            select(self.model)
            .options(selectinload(self.model.profile))
            .where(self.model.id == user_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_with_profile_by_email(self, email: str) -> User | None:
        query = (
            select(self.model)
            .options(selectinload(self.model.profile))
            .where(self.model.email == email)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_users_by_id_in(self, user_ids: list[str]) -> list[User]:
        query = select(self.model).where(self.model.id.in_(user_ids))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_users(self, exclude_deleted: bool = True) -> list[User]:
        query = select(self.model)
        if exclude_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def activate_user(self, user_id: str) -> None:
        stmt = update(self.model).where(self.model.id == user_id).values(is_active=True)
        await self.session.execute(stmt)

    async def deactivate_user(self, user_id: str) -> None:
        stmt = (
            update(self.model).where(self.model.id == user_id).values(is_active=False)
        )
        await self.session.execute(stmt)

    async def restore_user(self, user_id: str) -> None:
        stmt = (
            update(self.model).where(self.model.id == user_id).values(deleted_at=None)
        )
        await self.session.execute(stmt)

    async def soft_delete_user(self, user_id: str) -> None:
        stmt = (
            update(self.model)
            .where(and_(self.model.id == user_id, self.model.deleted_at.is_(None)))
            .values(deleted_at=func.now())
        )
        await self.session.execute(stmt)

    async def hard_delete_user(self, user_id: str) -> None:
        stmt = delete(self.model).where(self.model.id == user_id)
        await self.session.execute(stmt)

    async def is_email_taken(self, email: str) -> bool:
        query = select(exists().where(self.model.email == email))
        result = await self.session.execute(query)
        return result.scalar()
