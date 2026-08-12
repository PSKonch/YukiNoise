import asyncio
from collections.abc import Callable
from datetime import date
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.playlists.charts import ChartPlaylistUpdater, completed_period_bounds
from yn.modules.playlists.enums import SystemPlaylistKey
from yn.modules.tracks.metrics_repository import TrackMetricsRepository
from yn.shared.unit_of_work import UnitOfWork

POSTGRES_DIALECT = cast(Callable[[], Dialect], PGDialect)()


@pytest.mark.parametrize(
    ("key", "reference_date", "expected"),
    [
        (
            SystemPlaylistKey.TOP_DAY,
            date(2026, 8, 11),
            (date(2026, 8, 10), date(2026, 8, 11)),
        ),
        (
            SystemPlaylistKey.TOP_WEEK,
            date(2026, 8, 10),
            (date(2026, 8, 3), date(2026, 8, 10)),
        ),
        (
            SystemPlaylistKey.TOP_WEEK,
            date(2026, 8, 13),
            (date(2026, 8, 3), date(2026, 8, 10)),
        ),
        (
            SystemPlaylistKey.TOP_MONTH,
            date(2026, 9, 1),
            (date(2026, 8, 1), date(2026, 9, 1)),
        ),
        (
            SystemPlaylistKey.TOP_MONTH,
            date(2026, 1, 15),
            (date(2025, 12, 1), date(2026, 1, 1)),
        ),
    ],
)
def test_completed_period_bounds(
    key: SystemPlaylistKey,
    reference_date: date,
    expected: tuple[date, date],
) -> None:
    assert completed_period_bounds(key, reference_date) == expected


def test_refresh_replaces_chart_and_commits() -> None:
    async def run() -> None:
        track_ids = [uuid4(), uuid4()]
        metrics = SimpleNamespace(get_top_track_ids=AsyncMock(return_value=track_ids))
        playlists = SimpleNamespace(replace_system_chart=AsyncMock())
        uow = SimpleNamespace(
            track_metrics=metrics,
            playlists=playlists,
            commit=AsyncMock(),
        )

        await ChartPlaylistUpdater(
            cast(UnitOfWork, cast(Any, uow)),
            playlist_size=50,
        ).refresh(
            SystemPlaylistKey.TOP_MONTH,
            reference_date=date(2026, 9, 1),
        )

        metrics.get_top_track_ids.assert_awaited_once_with(
            period_start=date(2026, 8, 1),
            period_end=date(2026, 9, 1),
            limit=50,
        )
        playlists.replace_system_chart.assert_awaited_once_with(
            system_key=SystemPlaylistKey.TOP_MONTH,
            title="Топ месяца",
            description="Самые прослушиваемые треки за завершённый месяц.",
            period_start=date(2026, 8, 1),
            period_end=date(2026, 9, 1),
            track_ids=track_ids,
        )
        uow.commit.assert_awaited_once()

    asyncio.run(run())


def test_top_tracks_query_aggregates_period_and_filters_public_catalog() -> None:
    async def run() -> None:
        track_ids = [uuid4(), uuid4()]
        scalar_result = SimpleNamespace(all=lambda: track_ids)
        result = SimpleNamespace(scalars=lambda: scalar_result)
        session = AsyncMock(spec=AsyncSession)
        session.execute.return_value = result

        actual = await TrackMetricsRepository(session).get_top_track_ids(
            period_start=date(2026, 8, 1),
            period_end=date(2026, 9, 1),
            limit=100,
        )

        assert actual == track_ids
        statement = session.execute.await_args.args[0]
        compiled = statement.compile(dialect=POSTGRES_DIALECT)
        sql = str(compiled)
        assert "sum(track_metrics_daily.qualified_plays)" in sql
        assert "GROUP BY track_metrics_daily.track_id" in sql
        assert "tracks.deleted_at IS NULL" in sql
        assert "releases.deleted_at IS NULL" in sql
        assert "ORDER BY sum(track_metrics_daily.qualified_plays) DESC" in sql
        assert date(2026, 8, 1) in compiled.params.values()
        assert date(2026, 9, 1) in compiled.params.values()
        assert 100 in compiled.params.values()

    asyncio.run(run())
