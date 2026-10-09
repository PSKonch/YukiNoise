import asyncio
import importlib
import importlib.util
import os
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from sqlalchemy import Connection, func, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from yn.modules.artists.model import Artist
from yn.modules.auth.auth import get_current_user
from yn.modules.feed.route import router as feed_router
from yn.modules.follows.model import Follow
from yn.modules.notifications.kafka import notify_release_followers
from yn.modules.notifications.model import Notification
from yn.modules.notifications.repository import (
    NotificationRepository,
    ReleaseNotificationSource,
)
from yn.modules.notifications.route import router as notifications_router
from yn.modules.releases.enums import ReleaseStatus
from yn.modules.releases.events import RELEASE_EVENTS_TOPIC, ReleasePublishedEvent
from yn.modules.releases.model import Release
from yn.modules.tracks.model import Track
from yn.modules.users.dto import UserDTO
from yn.modules.users.model import User
from yn.shared.database import Base
from yn.shared.errors import register_exception_handlers
from yn.shared.outbox.model import OutboxModel
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork, get_uow

TEST_DSN = os.environ.get("YUKINOISE_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(
    not TEST_DSN, reason="Set YUKINOISE_TEST_PG_DSN to an isolated test database"
)


def migrate(connection: Connection, operation: str) -> None:
    path = (
        Path(__file__).resolve().parents[3]
        / "migrations/versions/b7e2a4c6d801_release_notifications.py"
    )
    spec = importlib.util.spec_from_file_location("notifications_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(connection)):
        getattr(module, operation)()


def test_publication_fanout_feed_privacy_and_read_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        assert TEST_DSN
        schema = f"notifications_{uuid4().hex}"
        setup = create_async_engine(TEST_DSN)
        engine = create_async_engine(
            TEST_DSN,
            connect_args={"server_settings": {"search_path": f"{schema},public"}},
        )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with setup.begin() as connection:
                for extension in ("vector", "pg_trgm"):
                    await connection.execute(
                        text(f"CREATE EXTENSION IF NOT EXISTS {extension}")
                    )
                await connection.execute(text(f"CREATE SCHEMA {schema}"))
            async with engine.begin() as connection:
                await connection.run_sync(
                    lambda conn: Base.metadata.create_all(conn, checkfirst=False)
                )
                await connection.run_sync(lambda conn: migrate(conn, "downgrade"))
                await connection.run_sync(lambda conn: migrate(conn, "upgrade"))

            now = datetime.now(UTC).replace(tzinfo=None)
            async with sessions.begin() as session:
                users = [
                    User(
                        id=uuid4(),
                        email=f"{uuid4()}@test.example",
                        hashed_password="test",
                    )
                    for _ in range(8)
                ]
                session.add_all(users)
                await session.flush()
                artists = [
                    Artist(
                        id=uuid4(), user_id=user.id, displayed_name=f"Artist {index}"
                    )
                    for index, user in enumerate(users)
                ]
                session.add_all(artists)
                await session.flush()
                owner, other, first, second, outsider, late, deleted, inactive = artists
                deleted.deleted_at = now
                users[-1].is_active = False
                session.add_all(
                    [
                        Follow(
                            follower_id=artist.id,
                            followed_id=owner.id,
                            created_at=now - timedelta(days=1),
                        )
                        for artist in (first, second, deleted, inactive)
                    ]
                )
                session.add(
                    Follow(
                        follower_id=late.id,
                        followed_id=owner.id,
                        created_at=now + timedelta(days=1),
                    )
                )
                session.add(
                    Follow(
                        follower_id=outsider.id,
                        followed_id=other.id,
                        created_at=now - timedelta(days=1),
                    )
                )
                due = Release(
                    id=uuid4(),
                    artist_id=owner.id,
                    title="New winter",
                    status=ReleaseStatus.SCHEDULED,
                    release_date=now - timedelta(minutes=1),
                )
                old = Release(
                    id=uuid4(),
                    artist_id=owner.id,
                    title="Old winter",
                    status=ReleaseStatus.PUBLISHED,
                    release_date=now - timedelta(days=3),
                )
                session.add_all(
                    [
                        due,
                        old,
                        Release(
                            artist_id=owner.id,
                            title="Draft",
                            status=ReleaseStatus.DRAFT,
                        ),
                        Release(
                            artist_id=owner.id,
                            title="Future",
                            status=ReleaseStatus.SCHEDULED,
                            release_date=now + timedelta(days=1),
                        ),
                        Release(
                            artist_id=owner.id,
                            title="Deleted",
                            status=ReleaseStatus.SCHEDULED,
                            release_date=now - timedelta(days=1),
                            deleted_at=now,
                        ),
                        Release(
                            artist_id=other.id,
                            title="Other artist",
                            status=ReleaseStatus.PUBLISHED,
                        ),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        Track(
                            release_id=due.id,
                            title="Visible",
                            duration_seconds=100,
                            track_number_in_release=1,
                            path="visible.mp3",
                        ),
                        Track(
                            release_id=due.id,
                            title="Removed",
                            duration_seconds=100,
                            track_number_in_release=2,
                            path="removed.mp3",
                            deleted_at=now,
                        ),
                    ]
                )

            task_module = importlib.import_module("yn.tasks.release_due_releases")
            monkeypatch.setattr(task_module, "async_primary_session", sessions)
            monkeypatch.setattr(settings, "discovery_enabled", False)

            # An outbox failure must roll back the publication itself.
            with patch.object(
                task_module,
                "record_release_published",
                side_effect=RuntimeError("outbox unavailable"),
            ):
                await task_module.release_due_releases()
            async with sessions() as session:
                assert (
                    await session.scalar(
                        select(Release.status).where(Release.id == due.id)
                    )
                    == ReleaseStatus.SCHEDULED
                )
                assert (
                    await session.scalar(select(func.count()).select_from(OutboxModel))
                    == 0
                )
            await task_module.release_due_releases()
            await task_module.release_due_releases()
            async with sessions() as session:
                events = (
                    (
                        await session.execute(
                            select(OutboxModel).where(
                                OutboxModel.topic == RELEASE_EVENTS_TOPIC
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(events) == 1
                event = ReleasePublishedEvent.model_validate(events[0].payload)
                assert event.release_id == due.id

            # Fail after one committed recipient, then redeliver twice.
            original = NotificationRepository.add_release_notifications
            calls = 0

            async def fail_second_batch(
                self: NotificationRepository,
                source: ReleaseNotificationSource,
                ids: Sequence[UUID],
                *,
                occurred_at: datetime,
            ) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("temporary outage")
                await original(self, source, ids, occurred_at=occurred_at)

            with patch.object(
                NotificationRepository, "add_release_notifications", fail_second_batch
            ):
                with pytest.raises(RuntimeError, match="temporary outage"):
                    await notify_release_followers(event, sessions, batch_size=1)
            async with sessions() as session:
                assert (
                    await session.scalar(select(func.count()).select_from(Notification))
                    == 1
                )
            await notify_release_followers(event, sessions, batch_size=1)
            await notify_release_followers(event, sessions, batch_size=1)
            async with sessions() as session:
                messages = (await session.execute(select(Notification))).scalars().all()
                assert {item.user_id for item in messages} == {
                    first.user_id,
                    second.user_id,
                }
                assert len(messages) == 2

            app = FastAPI()
            app.include_router(feed_router)
            app.include_router(notifications_router)
            register_exception_handlers(app)

            async def uow_dependency() -> AsyncIterator[UnitOfWork]:
                async with sessions() as session:
                    async with UnitOfWork(session) as uow:
                        yield uow

            app.dependency_overrides[get_uow] = uow_dependency

            def identity(artist: Artist | None, user_id: UUID | None = None) -> None:
                assert artist is not None or user_id is not None
                selected_id = artist.user_id if artist else user_id
                assert selected_id is not None
                user = UserDTO(
                    id=selected_id,
                    email="test@test.example",
                    role="user",
                    is_active=True,
                    artist_id=artist.id if artist else None,
                )
                app.dependency_overrides[get_current_user] = lambda: user

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                assert (await client.get("/me/feed/releases")).status_code == 401
                assert (await client.get("/notifications")).status_code == 401
                identity(first)
                feed = (await client.get("/me/feed/releases?limit=1")).json()
                assert [item["id"] for item in feed["items"]] == [str(due.id)]
                assert [track["title"] for track in feed["items"][0]["tracks"]] == [
                    "Visible"
                ]
                assert feed["has_more"] is True
                assert (await client.get("/me/feed/releases?limit=1&offset=1")).json()[
                    "items"
                ][0]["id"] == str(old.id)
                assert (
                    await client.get("/me/feed/releases?limit=101")
                ).status_code == 422
                page = (await client.get("/notifications")).json()
                assert page["unread_count"] == 1
                notification_id = page["items"][0]["id"]
                identity(second)
                assert (
                    await client.patch(f"/notifications/{notification_id}/read")
                ).status_code == 404
                assert (await client.get("/notifications/unread-count")).json()[
                    "unread_count"
                ] == 1
                identity(first)
                read = (
                    await client.patch(f"/notifications/{notification_id}/read")
                ).json()
                assert read["read_at"] is not None
                assert (
                    await client.patch(f"/notifications/{notification_id}/read")
                ).json()["read_at"] == read["read_at"]
                assert (await client.get("/notifications?unread_only=true")).json()[
                    "items"
                ] == []
                identity(second)
                assert (await client.post("/notifications/read-all")).json()[
                    "updated_count"
                ] == 1
                assert (await client.post("/notifications/read-all")).json()[
                    "updated_count"
                ] == 0
                identity(late)
                assert (await client.get("/notifications")).json()["items"] == []
                identity(outsider)
                assert [
                    item["title"]
                    for item in (await client.get("/me/feed/releases")).json()["items"]
                ] == ["Other artist"]
                identity(None, user_id=outsider.user_id)
                assert (await client.get("/me/feed/releases")).json() == {
                    "items": [],
                    "has_more": False,
                }
                async with sessions.begin() as session:
                    await session.execute(
                        update(Release)
                        .where(Release.id == due.id)
                        .values(deleted_at=now)
                    )
                identity(first)
                assert (await client.get("/notifications")).json()["items"] == []
                assert (await client.get("/notifications/unread-count")).json()[
                    "unread_count"
                ] == 0
                assert [
                    item["id"]
                    for item in (await client.get("/me/feed/releases")).json()["items"]
                ] == [str(old.id)]
        finally:
            await engine.dispose()
            async with setup.begin() as connection:
                await connection.execute(
                    text(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
                )
            await setup.dispose()

    asyncio.run(run())
