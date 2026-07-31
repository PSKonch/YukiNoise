"""add artist event outbox and idempotent system favorites playlist

Revision ID: 42a6b8d0c1e3
Revises: 7a1c9e4d2b30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "42a6b8d0c1e3"
down_revision: Union[str, Sequence[str], None] = "7a1c9e4d2b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("exchange", sa.String(length=255), nullable=False),
        sa.Column("routing_key", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_outbox_events_unpublished_created_at",
        "outbox_events",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("published_at IS NULL"),
    )
    op.drop_constraint(
        "playlists_artist_id_fkey",
        "playlists",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "playlists_artist_id_fkey",
        "playlists",
        "artists",
        ["artist_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "uq_playlists_artist_system_title",
        "playlists",
        ["artist_id", "title"],
        unique=True,
        postgresql_where=sa.text("playlist_type = 'SYSTEM'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_playlists_artist_system_title",
        table_name="playlists",
    )
    op.drop_constraint(
        "playlists_artist_id_fkey",
        "playlists",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "playlists_artist_id_fkey",
        "playlists",
        "artists",
        ["artist_id"],
        ["id"],
    )
    op.drop_index(
        "ix_outbox_events_unpublished_created_at",
        table_name="outbox_events",
    )
    op.drop_table("outbox_events")
