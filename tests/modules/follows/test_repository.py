import asyncio
from collections.abc import Callable
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.follows.repository import FollowRepository

POSTGRES_DIALECT = cast(Callable[[], Dialect], PGDialect)()


def test_follow_insert_is_idempotent() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)
        follower_id = uuid4()
        followed_id = uuid4()

        result = await FollowRepository(session).create(follower_id, followed_id)

        assert result is None
        statement = session.execute.await_args.args[0]
        compiled = statement.compile(dialect=POSTGRES_DIALECT)
        sql = str(compiled)
        assert "ON CONFLICT ON CONSTRAINT uq_follower_followed DO NOTHING" in sql
        assert "RETURNING follows.id" in sql
        assert follower_id in compiled.params.values()
        assert followed_id in compiled.params.values()

    asyncio.run(run())
