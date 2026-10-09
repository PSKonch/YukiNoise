import asyncio
import importlib.util
import os
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from sqlalchemy import Connection, delete, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from yn.modules.artists.model import Artist
from yn.modules.artists.service import ArtistService
from yn.modules.discovery.deps import (
    get_curator_service,
    get_discovery_service,
    get_discovery_user,
    require_discovery_enabled,
)
from yn.modules.discovery.indexer import TrackIndexer
from yn.modules.discovery.model import TrackEmbedding
from yn.modules.discovery.route import router
from yn.modules.discovery.schemas import GeneratedCuration, GeneratedTrack
from yn.modules.discovery.service import DiscoveryService
from yn.modules.releases.enums import ReleaseStatus
from yn.modules.releases.model import Release
from yn.modules.tracks.model import Track
from yn.modules.users.model import User
from yn.shared.cache.redis_cache import RedisCache
from yn.shared.database import Base
from yn.shared.errors import register_exception_handlers
from yn.shared.outbox.model import OutboxModel
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork

TEST_DSN = os.environ.get("YUKINOISE_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(
    not TEST_DSN, reason="Set YUKINOISE_TEST_PG_DSN to an isolated test database"
)


def test_metadata_migration_preserves_existing_documents_and_round_trips() -> None:
    async def run() -> None:
        assert TEST_DSN is not None
        engine = create_async_engine(TEST_DSN)
        migration_dir = Path(__file__).resolve().parents[3] / "migrations" / "versions"

        def migrate(connection: Connection, filename: str, operation: str) -> None:
            spec = importlib.util.spec_from_file_location(
                "discovery_test_migration", migration_dir / filename
            )
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with Operations.context(MigrationContext.configure(connection)):
                getattr(module, operation)()

        try:
            async with engine.begin() as connection:
                await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await connection.execute(text("CREATE SCHEMA migration_check"))
                await connection.execute(
                    text("SET search_path TO migration_check, public")
                )
                await connection.execute(
                    text("CREATE TABLE tracks (id uuid PRIMARY KEY)")
                )
                await connection.run_sync(
                    lambda conn: migrate(
                        conn, "c89a74f20aaa_track_embedding_model.py", "upgrade"
                    )
                )
                await connection.run_sync(
                    lambda conn: migrate(
                        conn,
                        "32bc8faa1b0f_track_embedding_model_768_vector.py",
                        "upgrade",
                    )
                )
                identifier = uuid4()
                await connection.execute(
                    text("INSERT INTO tracks (id) VALUES (:id)"), {"id": identifier}
                )
                await connection.execute(
                    text(
                        "INSERT INTO track_embedding (track_id, document_text, content_hash, document_schema_version, embedding_model, embedding_dimension, embedding_vector) VALUES (:id, 'text', 'hash', '1', 'test', 768, CAST(:vector AS vector))"
                    ),
                    {
                        "id": identifier,
                        "vector": "[" + ",".join(["1"] + ["0"] * 767) + "]",
                    },
                )
                for operation in ("upgrade", "downgrade", "upgrade"):
                    await connection.run_sync(
                        lambda conn: migrate(
                            conn,
                            "71e0f2a34d9b_track_embedding_metadata_types.py",
                            operation,
                        )
                    )
                    row = (
                        await connection.execute(
                            text(
                                "SELECT document_text, document_schema_version, indexed_at FROM track_embedding"
                            )
                        )
                    ).one()
                    assert row[0] == "text"
                    assert row[1] == ("1" if operation == "downgrade" else 1)
                    if operation != "downgrade":
                        assert (
                            isinstance(row[2], datetime) and row[2].tzinfo is not None
                        )
                await connection.execute(text("SET search_path TO public"))
                await connection.execute(text("DROP SCHEMA migration_check CASCADE"))
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_real_indexing_search_preview_and_artist_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        assert TEST_DSN is not None
        monkeypatch.setattr(settings, "discovery_enabled", True)
        engine = create_async_engine(TEST_DSN)
        sessions = async_sessionmaker(engine, expire_on_commit=False)

        class Provider:
            model_name = "test-provider"
            model_dimensions = 768
            calls = 0

            async def embed_query(self, query: str) -> tuple[float, ...]:
                return (1.0,) + (0.0,) * 767

            async def embed_documents(self, documents: Any) -> list[list[float]]:
                self.calls += 1
                return [[1.0] + [0.0] * 767 for _ in documents]

        class Generator:
            async def generate(
                self, *, query: str, candidates: Any, limit: int
            ) -> GeneratedCuration:
                valid = GeneratedTrack(
                    track_id=candidates[0].track_id,
                    reason="В жанрах указан ambient.",
                    sources=["track.genres"],
                )
                return GeneratedCuration(
                    title="Подборка",
                    summary="",
                    tracks=[
                        valid,
                        valid,
                        valid.model_copy(update={"track_id": uuid4()}),
                    ],
                )

        user_id, artist_id, release_id, track_id = (uuid4() for _ in range(4))
        try:
            async with engine.begin() as connection:
                for extension in ("vector", "pg_trgm"):
                    await connection.execute(
                        text(f"CREATE EXTENSION IF NOT EXISTS {extension}")
                    )
                await connection.run_sync(lambda conn: Base.metadata.create_all(conn))
            async with sessions.begin() as session:
                session.add_all(
                    [
                        User(
                            id=user_id,
                            email=f"{user_id}@example.test",
                            hashed_password="test",
                        ),
                        Artist(
                            id=artist_id,
                            user_id=user_id,
                            displayed_name=f"artist-{artist_id}",
                        ),
                        Release(
                            id=release_id,
                            artist_id=artist_id,
                            title="Winter",
                            status=ReleaseStatus.PUBLISHED,
                        ),
                        Track(
                            id=track_id,
                            release_id=release_id,
                            title="Snow",
                            duration_seconds=10,
                            track_number_in_release=1,
                            path="test.mp3",
                            genres=["ambient"],
                        ),
                    ]
                )
            provider = Provider()
            indexer = TrackIndexer(sessions, provider)
            assert await indexer.index_track(track_id) == "indexed"
            assert await indexer.index_track(track_id) == "skipped"
            assert provider.calls == 1
            async with sessions() as session:
                embedding = (
                    await session.execute(
                        select(TrackEmbedding).where(
                            TrackEmbedding.track_id == track_id
                        )
                    )
                ).scalar_one()
                assert embedding.document_schema_version == 1
                assert embedding.indexed_at.tzinfo is not None
                assert len(embedding.embedding_vector) == 768
            service = DiscoveryService(sessions, provider, Generator())
            assert [track.track_id for track in await service.search("ambient")] == [
                track_id
            ]
            assert [
                track.track_id
                for track in (await service.preview("ambient", limit=8)).tracks
            ] == [track_id]

            app = FastAPI()
            register_exception_handlers(app)
            app.include_router(router)
            app.dependency_overrides[require_discovery_enabled] = lambda: None
            app.dependency_overrides[get_discovery_user] = lambda: None
            app.dependency_overrides[get_discovery_service] = lambda: service
            app.dependency_overrides[get_curator_service] = lambda: service
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/discovery/search", json={"query": "  ambient  "}
                )
                assert response.status_code == 200
                assert response.json()[0]["track_id"] == str(track_id)
                response = await client.post(
                    "/discovery/curations/preview", json={"query": "ambient"}
                )
                assert (
                    response.status_code == 200 and len(response.json()["tracks"]) == 1
                )
                assert (
                    await client.post("/discovery/search", json={"query": " \t "})
                ).status_code == 422

            async with sessions() as session:
                async with UnitOfWork(session) as uow:
                    await ArtistService(
                        uow,
                        AsyncMock(spec=RedisCache),
                        cast(Any, None),
                        cast(Any, None),
                    ).update_artist(user_id, bio="Новая биография")
            assert await service.search("ambient") == []
            assert await indexer.index_track(track_id) == "indexed"
            async with sessions() as session:
                event = (
                    await session.execute(
                        select(OutboxModel).where(
                            OutboxModel.event_type == "artist.index_requested"
                        )
                    )
                ).scalar_one()
                assert event.payload["artist_id"] == str(artist_id)
            async with sessions.begin() as session:
                await session.execute(
                    update(Release)
                    .where(Release.id == release_id)
                    .values(status=ReleaseStatus.DRAFT)
                )
            assert await service.search("ambient") == []
            assert await indexer.index_track(track_id) == "deleted"
            async with sessions() as session:
                assert (
                    await session.execute(
                        select(TrackEmbedding).where(
                            TrackEmbedding.track_id == track_id
                        )
                    )
                ).scalar_one_or_none() is None
        finally:
            async with sessions.begin() as session:
                await session.execute(delete(User).where(User.id == user_id))
                await session.execute(
                    delete(OutboxModel).where(OutboxModel.message_key == str(artist_id))
                )
            await engine.dispose()

    asyncio.run(run())
