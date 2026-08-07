from datetime import date, datetime
from uuid import UUID as PyUUID

from sqlalchemy import UUID as SA_UUID
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from yn.shared.database import Base


class TrackMetricsDaily(Base):
    __tablename__ = "track_metrics_daily"
    __table_args__ = (
        CheckConstraint(
            "qualified_plays >= 0",
            name="ck_track_metrics_daily_qualified_plays_nonnegative",
        ),
        CheckConstraint(
            "likes_added >= 0",
            name="ck_track_metrics_daily_likes_added_nonnegative",
        ),
        CheckConstraint(
            "likes_removed >= 0",
            name="ck_track_metrics_daily_likes_removed_nonnegative",
        ),
        Index("ix_track_metrics_daily_date_track", "bucket_date", "track_id"),
    )

    track_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    bucket_date: Mapped[date] = mapped_column(Date, primary_key=True)

    qualified_plays: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    likes_added: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    likes_removed: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MetricEventReceipt(Base):
    __tablename__ = "metric_event_receipts"
    __table_args__ = (Index("ix_metric_event_receipts_processed_at", "processed_at"),)

    consumer: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        primary_key=True,
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
