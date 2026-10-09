"""Add featured artists to tracks.

Revision ID: a6d4e2f8b901
Revises: 71e0f2a34d9b
"""

import sqlalchemy as sa
from alembic import op

revision: str = "a6d4e2f8b901"
down_revision: str = "71e0f2a34d9b"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "track_features",
        sa.Column("track_id", sa.UUID(), nullable=False),
        sa.Column("artist_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("track_id", "artist_id"),
    )
    op.create_index("ix_track_features_artist_id", "track_features", ["artist_id"])


def downgrade() -> None:
    op.drop_index("ix_track_features_artist_id", table_name="track_features")
    op.drop_table("track_features")
