import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, PropertyMock, patch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.discovery.events import IndexScope
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork
from yn.tasks.index_track import index_source_embeddings, index_track_embedding


@pytest.mark.parametrize("scope", ["release", "artist"])
def test_source_indexing_pages_tracks_and_closes_sessions_before_queueing(
    monkeypatch: pytest.MonkeyPatch,
    scope: IndexScope,
) -> None:
    async def run() -> None:
        monkeypatch.setattr(settings, "discovery_enabled", True)
        identifier = UUID(int=10)
        ids = [UUID(int=value) for value in (1, 2, 3)]
        active_sessions = 0
        queued: list[str] = []
        repository = SimpleNamespace(
            get_track_ids=AsyncMock(side_effect=[ids[:2], ids[2:], []])
        )

        @asynccontextmanager
        async def sessions() -> AsyncIterator[AsyncSession]:
            nonlocal active_sessions
            active_sessions += 1
            try:
                yield AsyncMock(spec=AsyncSession)
            finally:
                active_sessions -= 1

        async def enqueue(track_id: str) -> None:
            assert active_sessions == 0
            queued.append(track_id)

        with patch("yn.tasks.index_track.async_primary_session", sessions):
            with patch.object(
                UnitOfWork, "track_embeddings", new_callable=PropertyMock
            ) as repo:
                repo.return_value = repository
                with patch.object(
                    index_track_embedding, "kiq", new_callable=AsyncMock
                ) as task:
                    task.side_effect = enqueue
                    assert await index_source_embeddings(str(identifier), scope) == 3
        assert queued == [str(track_id) for track_id in ids]
        calls = repository.get_track_ids.await_args_list
        assert [call.kwargs["after"] for call in calls] == [None, ids[1], ids[2]]
        assert all(call.kwargs["limit"] == 100 for call in calls)
        assert all(call.kwargs[f"{scope}_id"] == identifier for call in calls)

    asyncio.run(run())


def test_disabled_source_indexing_does_not_access_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "discovery_enabled", False)
    with patch("yn.tasks.index_track.async_primary_session") as sessions:
        assert asyncio.run(index_source_embeddings(str(UUID(int=1)), "release")) == 0
    sessions.assert_not_called()
