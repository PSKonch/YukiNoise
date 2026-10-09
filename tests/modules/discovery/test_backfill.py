import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, PropertyMock, patch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.discovery.backfill import backfill
from yn.modules.discovery.indexer import TrackIndexer
from yn.shared.unit_of_work import UnitOfWork


def test_backfill_saves_completed_pages_and_resumes(tmp_path: Path) -> None:
    async def run() -> None:
        ids = [UUID(int=value) for value in (1, 2, 3)]
        cursor = tmp_path / "cursor"
        session = AsyncMock(spec=AsyncSession)
        session.__aenter__.return_value = session
        repository = SimpleNamespace(
            get_track_ids=AsyncMock(side_effect=[ids[:2], ids[2:], []])
        )
        indexer = SimpleNamespace(
            index_track=AsyncMock(side_effect=["indexed", "skipped", "deleted"])
        )
        with patch.object(
            UnitOfWork, "track_embeddings", new_callable=PropertyMock
        ) as repo:
            repo.return_value = repository
            counts = await backfill(
                lambda: session, cast(TrackIndexer, indexer), cursor, page_size=2
            )
            assert counts == {"indexed": 1, "skipped": 1, "deleted": 1}
            assert cursor.read_text() == str(ids[-1])
            assert [
                call.kwargs["after"]
                for call in repository.get_track_ids.await_args_list
            ] == [None, ids[1], ids[2]]
            repository.get_track_ids.reset_mock(side_effect=True)
            repository.get_track_ids.return_value = []
            indexer.index_track.reset_mock()
            assert (
                await backfill(lambda: session, cast(TrackIndexer, indexer), cursor)
                == {}
            )
            assert repository.get_track_ids.await_args.kwargs["after"] == ids[-1]
            indexer.index_track.assert_not_awaited()

    asyncio.run(run())


@pytest.mark.parametrize("failure", [RuntimeError("provider unavailable"), "stale"])
def test_backfill_does_not_advance_a_failed_page(
    tmp_path: Path, failure: object
) -> None:
    async def run() -> None:
        previous = UUID(int=1)
        ids = [UUID(int=2), UUID(int=3)]
        cursor = tmp_path / "cursor"
        cursor.write_text(str(previous))
        session = AsyncMock(spec=AsyncSession)
        session.__aenter__.return_value = session
        repository = SimpleNamespace(get_track_ids=AsyncMock(return_value=ids))
        indexer = SimpleNamespace(
            index_track=AsyncMock(side_effect=["indexed", failure])
        )
        with patch.object(
            UnitOfWork, "track_embeddings", new_callable=PropertyMock
        ) as repo:
            repo.return_value = repository
            with pytest.raises(RuntimeError):
                await backfill(lambda: session, cast(TrackIndexer, indexer), cursor)
        assert cursor.read_text() == str(previous)

    asyncio.run(run())


def test_dry_run_restart_does_not_change_the_checkpoint(tmp_path: Path) -> None:
    async def run() -> None:
        cursor = tmp_path / "cursor"
        cursor.write_text(str(UUID(int=10)))
        session = AsyncMock(spec=AsyncSession)
        session.__aenter__.return_value = session
        repository = SimpleNamespace(
            get_track_ids=AsyncMock(side_effect=[[UUID(int=1)], []])
        )
        indexer = SimpleNamespace(index_track=AsyncMock(return_value="pending"))
        with patch.object(
            UnitOfWork, "track_embeddings", new_callable=PropertyMock
        ) as repo:
            repo.return_value = repository
            counts = await backfill(
                lambda: session,
                cast(TrackIndexer, indexer),
                cursor,
                dry_run=True,
                restart=True,
            )
        assert counts == {"pending": 1}
        assert cursor.read_text() == str(UUID(int=10))
        assert repository.get_track_ids.await_args_list[0].kwargs["after"] is None
        indexer.index_track.assert_awaited_once_with(UUID(int=1), dry_run=True)

    asyncio.run(run())


def test_backfill_rejects_an_invalid_page_size_before_accessing_database(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="Page size"):
        asyncio.run(
            backfill(cast(Any, None), cast(Any, None), tmp_path / "cursor", page_size=0)
        )
