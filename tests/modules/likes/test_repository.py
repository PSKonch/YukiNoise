import asyncio
from collections.abc import Callable
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.likes.enums import TargetType
from yn.modules.likes.model import Like
from yn.modules.likes.repository import LikeRepository

POSTGRES_DIALECT = cast(Callable[[], Dialect], PGDialect)()


def test_like_insert_is_idempotent() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)

        await LikeRepository(session).create(
            uuid4(),
            TargetType.POST,
            uuid4(),
        )

        statement = session.execute.await_args.args[0]
        sql = str(statement.compile(dialect=POSTGRES_DIALECT))
        assert "ON CONFLICT ON CONSTRAINT uq_likes_artist_target DO NOTHING" in sql
        assert "RETURNING likes.id" in sql
        session.execute.assert_awaited_once()

    asyncio.run(run())


def test_track_like_does_not_update_counter_in_likes_repository() -> None:
    async def run() -> None:
        like = cast(Like, SimpleNamespace(id=uuid4()))
        insert_result = SimpleNamespace(scalar_one_or_none=lambda: like)
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = insert_result

        result = await LikeRepository(session).create(
            uuid4(),
            TargetType.TRACK,
            uuid4(),
        )

        assert result is like
        session.execute.assert_awaited_once()

    asyncio.run(run())
