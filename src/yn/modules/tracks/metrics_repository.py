from collections.abc import Mapping
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.tracks.metrics_model import MetricEventReceipt, TrackMetricsDaily

TRACK_LIKE_METRICS_CONSUMER = "track_metrics.likes.v1"


def utc_bucket_date(occurred_at: datetime | None = None) -> date:
    timestamp = occurred_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).date()


class TrackMetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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

    async def mark_event_processed(
        self,
        event_id: UUID,
        *,
        consumer: str = TRACK_LIKE_METRICS_CONSUMER,
    ) -> bool:
        statement = (
            pg_insert(MetricEventReceipt)
            .values(consumer=consumer, event_id=event_id)
            .on_conflict_do_nothing(
                index_elements=[
                    MetricEventReceipt.consumer,
                    MetricEventReceipt.event_id,
                ]
            )
            .returning(MetricEventReceipt.event_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

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
