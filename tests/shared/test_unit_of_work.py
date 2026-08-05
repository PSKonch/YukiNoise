import asyncio
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from yn.shared.unit_of_work import UnitOfWork


def test_context_exit_does_not_commit_implicitly() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)

        async with UnitOfWork(session):
            pass

        session.commit.assert_not_awaited()
        session.rollback.assert_awaited_once()

    asyncio.run(run())


def test_explicit_commit_is_the_only_commit() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)

        async with UnitOfWork(session) as uow:
            await uow.commit()

        session.commit.assert_awaited_once()
        session.rollback.assert_awaited_once()

    asyncio.run(run())
