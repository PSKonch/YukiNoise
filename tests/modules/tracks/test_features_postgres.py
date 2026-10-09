import asyncio
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Connection, delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from yn.modules.artists.model import Artist
from yn.modules.discovery.repository import TrackEmbeddingRepository
from yn.modules.releases.enums import ReleaseStatus
from yn.modules.releases.model import Release
from yn.modules.tracks.dto import TrackDTO
from yn.modules.tracks.model import Track, TrackFeature
from yn.modules.tracks.repository import TrackRepository
from yn.modules.users.model import User
from yn.shared.database import Base

TEST_DSN = os.environ.get("YUKINOISE_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(
    not TEST_DSN, reason="Set YUKINOISE_TEST_PG_DSN to an isolated test database"
)


def migrate(connection: Connection, operation: str) -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "migrations"
        / "versions"
        / "a6d4e2f8b901_track_features.py"
    )
    spec = importlib.util.spec_from_file_location("track_features_migration", migration)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(connection)):
        getattr(module, operation)()


def test_features_migration_persistence_visibility_and_cascades() -> None:
    async def run() -> None:
        assert TEST_DSN is not None
        engine = create_async_engine(TEST_DSN)
        try:
            async with engine.connect() as connection:
                transaction = await connection.begin()
                try:
                    for extension in ("vector", "pg_trgm"):
                        await connection.execute(
                            text(f"CREATE EXTENSION IF NOT EXISTS {extension}")
                        )
                    schema = f"track_features_{uuid4().hex}"
                    await connection.execute(text(f"CREATE SCHEMA {schema}"))
                    await connection.execute(
                        text(f"SET LOCAL search_path TO {schema}, public")
                    )
                    await connection.run_sync(
                        lambda conn: Base.metadata.create_all(conn, checkfirst=False)
                    )
                    await connection.run_sync(lambda conn: migrate(conn, "downgrade"))
                    await connection.run_sync(lambda conn: migrate(conn, "upgrade"))
                    async with AsyncSession(
                        bind=connection,
                        expire_on_commit=False,
                        join_transaction_mode="create_savepoint",
                    ) as session:
                        artists = [
                            Artist(id=uuid4(), user_id=uuid4(), displayed_name=name)
                            for name in ("Owner", "Guest B", "Guest A")
                        ]
                        for artist in artists:
                            session.add(
                                User(
                                    id=artist.user_id,
                                    email=f"{artist.id}@test.example",
                                    hashed_password="test",
                                )
                            )
                        await session.flush()
                        session.add_all(artists)
                        await session.flush()
                        owner, guest_b, guest_a = artists
                        release = Release(
                            id=uuid4(),
                            artist_id=owner.id,
                            title="Winter",
                            status=ReleaseStatus.DRAFT,
                        )
                        session.add(release)
                        await session.flush()
                        repository = TrackRepository(session)
                        track = await repository.create(
                            track_id=uuid4(),
                            release_id=release.id,
                            title="Snow",
                            track_number_in_release=1,
                            duration_seconds=120,
                            path="snow.mp3",
                            genres=["ambient"],
                            featured_artist_ids=[guest_b.id, guest_a.id],
                        )
                        await session.commit()
                        assert [
                            artist.displayed_name
                            for artist in TrackDTO.from_orm(track).featured_artists
                        ] == ["Guest A", "Guest B"]
                        assert not await repository.get_tracks_by_artist_id(
                            guest_a.id, limit=10, offset=0
                        )
                        await session.execute(
                            update(Release)
                            .where(Release.id == release.id)
                            .values(status=ReleaseStatus.PUBLISHED)
                        )
                        await session.commit()
                        session.expunge_all()
                        for artist_id in (owner.id, guest_a.id, guest_b.id):
                            tracks = await repository.get_tracks_by_artist_id(
                                artist_id, limit=10, offset=0
                            )
                            assert [item.id for item in tracks] == [track.id]
                            assert (
                                len(TrackDTO.from_orm(tracks[0]).featured_artists) == 2
                            )
                        assert not await repository.get_owned_tracks_by_artist_id(
                            guest_a.id, limit=10, offset=0
                        )
                        assert (
                            await repository.get_track_by_id_for_artist(
                                track.id, guest_a.id
                            )
                            is None
                        )
                        assert await TrackEmbeddingRepository(session).get_track_ids(
                            artist_id=guest_a.id
                        ) == [track.id]
                        renamed = await repository.update(
                            track_id=track.id, release_id=release.id, title="New snow"
                        )
                        assert (
                            renamed is not None and len(renamed.featured_artists) == 2
                        )
                        replaced = await repository.update(
                            track_id=track.id,
                            release_id=release.id,
                            featured_artist_ids=[guest_b.id],
                        )
                        assert replaced is not None and [
                            artist.id for artist in replaced.featured_artists
                        ] == [guest_b.id]
                        assert not await repository.get_tracks_by_artist_id(
                            guest_a.id, limit=10, offset=0
                        )
                        await session.execute(
                            delete(Artist).where(Artist.id == guest_b.id)
                        )
                        await session.commit()
                        session.expunge_all()
                        remaining = await repository.get_track_by_id(track.id)
                        assert remaining is not None and not remaining.featured_artists
                        assert (
                            not (await session.execute(select(TrackFeature)))
                            .scalars()
                            .all()
                        )
                        cleared = await repository.update(
                            track_id=track.id,
                            release_id=release.id,
                            featured_artist_ids=[],
                        )
                        assert cleared is not None and not cleared.featured_artists
                        await repository.update(
                            track_id=track.id,
                            release_id=release.id,
                            featured_artist_ids=[guest_a.id],
                        )
                        await session.execute(delete(Track).where(Track.id == track.id))
                        assert (
                            not (await session.execute(select(TrackFeature)))
                            .scalars()
                            .all()
                        )
                        await session.commit()
                    await connection.run_sync(lambda conn: migrate(conn, "downgrade"))
                    assert (
                        await connection.scalar(text("SELECT count(*) FROM releases"))
                        == 1
                    )
                finally:
                    await transaction.rollback()
        finally:
            await engine.dispose()

    asyncio.run(run())
