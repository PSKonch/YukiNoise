"""remove obsolete playback event history

Revision ID: 7a1c9e4d2b30
Revises: 5f3d8c1a7b2e
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7a1c9e4d2b30"
down_revision: Union[str, Sequence[str], None] = "5f3d8c1a7b2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("playback_session_events")


def downgrade() -> None:
    op.create_table(
        "playback_session_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "track_id",
            sa.UUID(),
            sa.ForeignKey("tracks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("listened_seconds", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("is_paused", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
    )
    for column in ("user_id", "track_id", "session_id", "is_active"):
        op.create_index(
            f"ix_playback_session_events_{column}", "playback_session_events", [column]
        )
