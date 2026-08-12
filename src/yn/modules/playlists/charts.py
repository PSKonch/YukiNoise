from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from yn.modules.playlists.enums import SystemPlaylistKey
from yn.shared.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class ChartDefinition:
    key: SystemPlaylistKey
    title: str
    description: str


CHART_DEFINITIONS = {
    SystemPlaylistKey.TOP_DAY: ChartDefinition(
        key=SystemPlaylistKey.TOP_DAY,
        title="Топ дня",
        description="Самые прослушиваемые треки за день",
    ),
    SystemPlaylistKey.TOP_WEEK: ChartDefinition(
        key=SystemPlaylistKey.TOP_WEEK,
        title="Топ недели",
        description="Самые прослушиваемые треки за неделю",
    ),
    SystemPlaylistKey.TOP_MONTH: ChartDefinition(
        key=SystemPlaylistKey.TOP_MONTH,
        title="Топ месяца",
        description="Самые прослушиваемые треки за месяц",
    ),
}


def completed_period_bounds(
    key: SystemPlaylistKey,
    reference_date: date,
) -> tuple[date, date]:
    if key == SystemPlaylistKey.TOP_DAY:
        return reference_date - timedelta(days=1), reference_date

    if key == SystemPlaylistKey.TOP_WEEK:
        current_week_start = reference_date - timedelta(days=reference_date.weekday())
        return current_week_start - timedelta(days=7), current_week_start

    current_month_start = reference_date.replace(day=1)
    previous_month_end = current_month_start - timedelta(days=1)
    return previous_month_end.replace(day=1), current_month_start


class ChartPlaylistUpdater:
    def __init__(self, uow: UnitOfWork, *, playlist_size: int = 100) -> None:
        self._uow = uow
        self._playlist_size = playlist_size

    async def refresh(
        self,
        key: SystemPlaylistKey,
        *,
        reference_date: date | None = None,
    ) -> None:
        definition = CHART_DEFINITIONS[key]
        today = reference_date or datetime.now(UTC).date()
        period_start, period_end = completed_period_bounds(key, today)
        track_ids = await self._uow.track_metrics.get_top_track_ids(
            period_start=period_start,
            period_end=period_end,
            limit=self._playlist_size,
        )
        await self._uow.playlists.replace_system_chart(
            system_key=key,
            title=definition.title,
            description=definition.description,
            period_start=period_start,
            period_end=period_end,
            track_ids=track_ids,
        )
        await self._uow.commit()
