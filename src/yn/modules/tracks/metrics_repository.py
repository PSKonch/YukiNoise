from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.releases.model import Release
from yn.modules.tracks.metrics_model import TrackMetricsDaily
from yn.modules.tracks.model import Track


def utc_bucket_date(occurred_at: datetime | None = None) -> date:
    timestamp = occurred_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).date()


class TrackMetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_top_track_ids(
        self,
        *,
        period_start: date,
        period_end: date,
        limit: int,
    ) -> Sequence[UUID]:
        plays = func.sum(TrackMetricsDaily.qualified_plays)
        statement = (
            select(TrackMetricsDaily.track_id)
            .join(Track, Track.id == TrackMetricsDaily.track_id)
            .join(Release, Release.id == Track.release_id)
            .where(
                and_(
                    TrackMetricsDaily.bucket_date >= period_start,
                    TrackMetricsDaily.bucket_date < period_end,
                    Track.deleted_at.is_(None),
                    Release.publicly_visible_clause(),
                )
            )
            .group_by(TrackMetricsDaily.track_id)
            .having(plays > 0)
            .order_by(plays.desc(), TrackMetricsDaily.track_id.asc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def increment_qualified_plays(
        self,
        play_counts: Mapping[tuple[UUID, date], int],
    ) -> None:
        if not play_counts:
            return

        insert_statement = pg_insert(TrackMetricsDaily).values(
            [
                {
                    "track_id": track_id,
                    "bucket_date": bucket_date,
                    "qualified_plays": count,
                    "likes_added": 0,
                    "likes_removed": 0,
                }
                for (track_id, bucket_date), count in play_counts.items()
            ]
        )
        statement = insert_statement.on_conflict_do_update(
            index_elements=[
                TrackMetricsDaily.track_id,
                TrackMetricsDaily.bucket_date,
            ],
            set_={
                "qualified_plays": (
                    TrackMetricsDaily.qualified_plays
                    + insert_statement.excluded.qualified_plays
                ),
                "updated_at": func.now(),
            },
        )
        await self._session.execute(statement)

    async def increment_likes(
        self,
        *,
        track_id: UUID,
        bucket_date: date,
        added: bool,
    ) -> None:
        metric_name = "likes_added" if added else "likes_removed"
        insert_statement = pg_insert(TrackMetricsDaily).values(
            track_id=track_id,
            bucket_date=bucket_date,
            qualified_plays=0,
            likes_added=1 if added else 0,
            likes_removed=0 if added else 1,
        )
        statement = insert_statement.on_conflict_do_update(
            index_elements=[
                TrackMetricsDaily.track_id,
                TrackMetricsDaily.bucket_date,
            ],
            set_={
                metric_name: (
                    getattr(TrackMetricsDaily, metric_name)
                    + getattr(insert_statement.excluded, metric_name)
                ),
                "updated_at": func.now(),
            },
        )
        await self._session.execute(statement)
