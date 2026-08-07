"""add daily track metrics

Revision ID: d8e4a9b6c201
Revises: f43fcf8ab2e0
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8e4a9b6c201"
down_revision: Union[str, Sequence[str], None] = "f43fcf8ab2e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "track_metrics_daily",
        sa.Column("track_id", sa.UUID(), nullable=False),
        sa.Column("bucket_date", sa.Date(), nullable=False),
        sa.Column(
            "qualified_plays",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "likes_added",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "likes_removed",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "likes_added >= 0",
            name="ck_track_metrics_daily_likes_added_nonnegative",
        ),
        sa.CheckConstraint(
            "likes_removed >= 0",
            name="ck_track_metrics_daily_likes_removed_nonnegative",
        ),
        sa.CheckConstraint(
            "qualified_plays >= 0",
            name="ck_track_metrics_daily_qualified_plays_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("track_id", "bucket_date"),
    )
    op.create_index(
        "ix_track_metrics_daily_date_track",
        "track_metrics_daily",
        ["bucket_date", "track_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_track_metrics_daily_date_track",
        table_name="track_metrics_daily",
    )
    op.drop_table("track_metrics_daily")
