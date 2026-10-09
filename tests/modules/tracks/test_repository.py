import asyncio
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.discovery.repository import TrackEmbeddingRepository
from yn.modules.tracks.repository import TrackRepository

POSTGRES_DIALECT = cast(Callable[[], Dialect], PGDialect)()


@pytest.mark.parametrize("owned", [False, True])
def test_public_artist_tracks_include_features_and_owner_tracks_stay_separate(
    owned: bool,
) -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: [])
        )
        artist_id = uuid4()
        repository = TrackRepository(session)
        if owned:
            await repository.get_owned_tracks_by_artist_id(artist_id, limit=5, offset=2)
        else:
            await repository.get_tracks_by_artist_id(artist_id, limit=5, offset=2)

        statement = session.execute.await_args.args[0]
        compiled = statement.compile(dialect=POSTGRES_DIALECT)
        sql = str(compiled)
        assert "releases.artist_id =" in sql
        assert "tracks.deleted_at IS NULL" in sql
        assert "releases.deleted_at IS NULL" in sql
        assert ("EXISTS" in sql) is not owned
        if not owned:
            assert "track_features.artist_id" in sql
            assert "artists.deleted_at IS NULL" in sql
            assert "releases.status" in sql
        assert artist_id in compiled.params.values()

    asyncio.run(run())


def test_artist_reindexing_includes_features_without_join_duplicates() -> None:
    async def run() -> None:
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: [])
        )

        await TrackEmbeddingRepository(session).get_track_ids(
            artist_id=uuid4(), limit=100
        )

        statement = session.execute.await_args.args[0]
        sql = str(statement.compile(dialect=POSTGRES_DIALECT))
        assert "releases.artist_id =" in sql
        assert "EXISTS" in sql
        assert "track_features.artist_id" in sql

    asyncio.run(run())


@pytest.mark.parametrize("clear", [False, True])
def test_feature_only_update_locks_track_and_refreshes_relationship(
    clear: bool,
) -> None:
    async def run() -> None:
        track = SimpleNamespace(id=uuid4())
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: track)
        ids = [] if clear else [uuid4(), uuid4()]

        result = await TrackRepository(session).update(
            track_id=track.id, release_id=uuid4(), featured_artist_ids=ids
        )

        assert result is cast(Any, track)
        statements = [
            str(call.args[0].compile(dialect=POSTGRES_DIALECT))
            for call in session.execute.await_args_list
        ]
        assert "FOR UPDATE" in statements[0]
        assert "tracks.deleted_at IS NULL" in statements[0]
        assert statements[1].startswith("DELETE FROM track_features")
        if not clear:
            assert statements[2].startswith("INSERT INTO track_features")
        else:
            assert len(statements) == 2
        session.refresh.assert_awaited_once_with(cast(Any, track), ["featured_artists"])
        session.commit.assert_not_awaited()

    asyncio.run(run())
