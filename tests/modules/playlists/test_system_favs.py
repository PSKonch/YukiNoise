import asyncio
from collections.abc import Callable
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.playlists.repository import PlaylistsRepository

POSTGRES_DIALECT = cast(Callable[[], Dialect], PGDialect)()


def test_system_favs_insert_is_idempotent() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        artist_id = uuid4()

        await PlaylistsRepository(session).create_system_favs(artist_id)

        statement = session.execute.await_args.args[0]
        compiled = statement.compile(dialect=POSTGRES_DIALECT)
        sql = str(compiled)
        assert "ON CONFLICT (artist_id, title)" in sql
        assert "WHERE playlist_type =" in sql
        assert "DO NOTHING" in sql
        assert artist_id in compiled.params.values()
        assert "favs" in compiled.params.values()
        assert True in compiled.params.values()

    asyncio.run(run())
