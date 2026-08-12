import logging

from yn.modules.playlists.charts import ChartPlaylistUpdater
from yn.modules.playlists.enums import SystemPlaylistKey
from yn.shared.database import async_primary_session
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork
from yn.tasks.broker import broker

logger = logging.getLogger(__name__)


async def _refresh_chart(system_key: SystemPlaylistKey) -> None:
    async with async_primary_session() as session:
        try:
            async with UnitOfWork(session) as uow:
                updater = ChartPlaylistUpdater(
                    uow,
                    playlist_size=settings.chart_playlist_size,
                )
                await updater.refresh(system_key)
            logger.info("Refreshed system chart playlist", extra={"key": system_key})
        except Exception:
            logger.exception(
                "Failed to refresh system chart playlist",
                extra={"key": system_key},
            )
            raise


@broker.task(schedule=[{"cron": "5 0 * * *", "cron_offset": "UTC"}])
async def refresh_daily_chart() -> None:
    await _refresh_chart(SystemPlaylistKey.TOP_DAY)


@broker.task(schedule=[{"cron": "10 0 * * 1", "cron_offset": "UTC"}])
async def refresh_weekly_chart() -> None:
    await _refresh_chart(SystemPlaylistKey.TOP_WEEK)


@broker.task(schedule=[{"cron": "15 0 1 * *", "cron_offset": "UTC"}])
async def refresh_monthly_chart() -> None:
    await _refresh_chart(SystemPlaylistKey.TOP_MONTH)
