import asyncio
from collections.abc import Callable
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.commentaries.model import Commentary
from yn.modules.commentaries.repository import CommentaryRepository

POSTGRES_DIALECT = cast(Callable[[], Dialect], PGDialect)()


def test_create_commentary_uses_expected_relationships() -> None:
    async def run() -> None:
        commentary = cast(Commentary, SimpleNamespace(id=uuid4()))
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = SimpleNamespace(scalar_one=lambda: commentary)
        artist_id = uuid4()
        post_id = uuid4()
        parent_id = uuid4()

        result = await CommentaryRepository(session).create(
            artist_id=artist_id,
            post_id=post_id,
            commentary_id=parent_id,
            content="Reply",
        )

        assert result is commentary
        statement = session.execute.await_args.args[0]
        compiled = statement.compile(dialect=POSTGRES_DIALECT)
        assert "INSERT INTO commentaries" in str(compiled)
        assert "RETURNING commentaries.id" in str(compiled)
        for value in (artist_id, post_id, parent_id, "Reply"):
            assert value in compiled.params.values()

    asyncio.run(run())


def test_soft_delete_is_scoped_to_owner_and_active_commentary() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = SimpleNamespace(
            scalar_one_or_none=lambda: uuid4()
        )
        commentary_id = uuid4()
        artist_id = uuid4()

        deleted = await CommentaryRepository(session).soft_delete(
            commentary_id=commentary_id,
            artist_id=artist_id,
        )

        assert deleted is True
        statement = session.execute.await_args.args[0]
        compiled = statement.compile(dialect=POSTGRES_DIALECT)
        sql = str(compiled)
        assert "UPDATE commentaries" in sql
        assert "commentaries.artist_id" in sql
        assert "commentaries.deleted_at IS NULL" in sql
        assert commentary_id in compiled.params.values()
        assert artist_id in compiled.params.values()

    asyncio.run(run())
