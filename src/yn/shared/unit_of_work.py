from typing import TYPE_CHECKING, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from yn.shared.database import get_session

if TYPE_CHECKING:
    from yn.modules.profiles.repository import ProfileRepository
    from yn.modules.users.repository import UserRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._users_repo: "UserRepository | None" = None
        self._profiles_repo: "ProfileRepository | None" = None

    @property
    def users(self) -> "UserRepository":
        return self._users_repo

    @property
    def profiles(self) -> "ProfileRepository":
        return self._profiles_repo

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc:
            await self._session.rollback()
        else:
            await self._session.commit()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()


async def get_uow() -> AsyncGenerator["UnitOfWork", None]:
    async for session in get_session():
        async with UnitOfWork(session) as uow:
            yield uow
