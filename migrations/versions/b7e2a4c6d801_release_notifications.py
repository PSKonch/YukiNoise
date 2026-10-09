"""Deduplicate release notifications and index unread messages.

Revision ID: b7e2a4c6d801
Revises: a6d4e2f8b901
"""

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2a4c6d801"
down_revision: str = "a6d4e2f8b901"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("release_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_notifications_release",
        "notifications",
        "releases",
        ["release_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_notifications_user_release",
        "notifications",
        ["user_id", "release_id"],
    )
    op.create_index(
        "ix_notifications_unread_user",
        "notifications",
        ["user_id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_unread_user", table_name="notifications")
    op.drop_constraint("uq_notifications_user_release", "notifications", type_="unique")
    op.drop_constraint("fk_notifications_release", "notifications", type_="foreignkey")
    op.drop_column("notifications", "release_id")
