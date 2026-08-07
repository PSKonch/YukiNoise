"""modernize outbox model

Revision ID: 03648cac3bdc
Revises: a4c2d8e6f103
Create Date: 2026-08-07 14:19:25.279803

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "03648cac3bdc"
down_revision: Union[str, Sequence[str], None] = "a4c2d8e6f103"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(
        "ix_outbox_events_unpublished_created_at",
        table_name="outbox_events",
    )
    op.rename_table("outbox_events", "outbox")
    op.execute("ALTER TABLE outbox RENAME CONSTRAINT outbox_events_pkey TO outbox_pkey")
    op.alter_column(
        "outbox",
        "exchange",
        existing_type=sa.String(length=255),
        new_column_name="topic",
        existing_nullable=False,
    )
    op.alter_column(
        "outbox",
        "event_type",
        existing_type=sa.String(length=100),
        type_=sa.String(length=255),
        existing_nullable=False,
    )

    op.add_column("outbox", sa.Column("version", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE outbox
        SET version = CASE
            WHEN payload->>'version' ~ '^[1-9][0-9]*$'
                THEN (payload->>'version')::integer
            ELSE 1
        END
        """
    )
    op.alter_column(
        "outbox",
        "version",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("1"),
    )
    op.add_column(
        "outbox",
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "outbox",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_column("outbox", "routing_key")
    op.drop_column("outbox", "occurred_at")

    op.create_index(
        "ix_outbox_unpublished_created_at",
        "outbox",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("published_at IS NULL"),
    )
    op.create_index(
        "ix_outbox_unpublished_next_attempt_at",
        "outbox",
        ["next_attempt_at"],
        unique=False,
        postgresql_where=sa.text("published_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_outbox_unpublished_next_attempt_at",
        table_name="outbox",
    )
    op.drop_index("ix_outbox_unpublished_created_at", table_name="outbox")

    op.add_column(
        "outbox",
        sa.Column("routing_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "outbox",
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE outbox
        SET routing_key = event_type || '.v' || version,
            occurred_at = created_at
        """
    )
    op.alter_column(
        "outbox",
        "routing_key",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "outbox",
        "occurred_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.drop_column("outbox", "next_attempt_at")
    op.drop_column("outbox", "attempts")
    op.drop_column("outbox", "version")
    op.alter_column(
        "outbox",
        "event_type",
        existing_type=sa.String(length=255),
        type_=sa.String(length=100),
        existing_nullable=False,
    )
    op.alter_column(
        "outbox",
        "topic",
        existing_type=sa.String(length=255),
        new_column_name="exchange",
        existing_nullable=False,
    )
    op.rename_table("outbox", "outbox_events")
    op.execute(
        "ALTER TABLE outbox_events RENAME CONSTRAINT outbox_pkey TO outbox_events_pkey"
    )
    op.create_index(
        "ix_outbox_events_unpublished_created_at",
        "outbox_events",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("published_at IS NULL"),
    )
