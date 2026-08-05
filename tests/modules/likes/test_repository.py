import asyncio
from collections.abc import Callable
from datetime import datetime
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


def test_track_like_updates_counter_only_after_insert() -> None:
    async def run() -> None:
        like = Like(
            id=uuid4(),
            artist_id=uuid4(),
            target_type=TargetType.TRACK,
            target_id=uuid4(),
            created_at=datetime.now(),
        )
        insert_result = SimpleNamespace(scalar_one_or_none=lambda: like)
        update_result = SimpleNamespace()
        session = AsyncMock(spec=AsyncSession)
        session.execute.side_effect = [insert_result, update_result]

        result = await LikeRepository(session).create(
            uuid4(),
            TargetType.TRACK,
            uuid4(),
        )

        assert result is like
        assert session.execute.await_count == 2
        update_statement = session.execute.await_args_list[1].args[0]
        sql = str(update_statement.compile(dialect=POSTGRES_DIALECT))
        assert "UPDATE tracks SET like_count=(tracks.like_count +" in sql

    asyncio.run(run())
