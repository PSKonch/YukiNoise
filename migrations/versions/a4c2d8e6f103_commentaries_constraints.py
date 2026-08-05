"""add commentary foreign key actions and parent index

Revision ID: a4c2d8e6f103
Revises: 5d6f7a8b9c10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a4c2d8e6f103"
down_revision: Union[str, Sequence[str], None] = "5d6f7a8b9c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "commentaries_artist_id_fkey", "commentaries", type_="foreignkey"
    )
    op.drop_constraint("commentaries_post_id_fkey", "commentaries", type_="foreignkey")
    op.drop_constraint(
        "commentaries_commentary_id_fkey", "commentaries", type_="foreignkey"
    )
    op.create_foreign_key(
        "commentaries_artist_id_fkey",
        "commentaries",
        "artists",
        ["artist_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "commentaries_post_id_fkey",
        "commentaries",
        "posts",
        ["post_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "commentaries_commentary_id_fkey",
        "commentaries",
        "commentaries",
        ["commentary_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_commentaries_commentary_id_created_at",
        "commentaries",
        ["commentary_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_commentaries_commentary_id_created_at", table_name="commentaries")
    op.drop_constraint(
        "commentaries_commentary_id_fkey", "commentaries", type_="foreignkey"
    )
    op.drop_constraint("commentaries_post_id_fkey", "commentaries", type_="foreignkey")
    op.drop_constraint(
        "commentaries_artist_id_fkey", "commentaries", type_="foreignkey"
    )
    op.create_foreign_key(
        "commentaries_commentary_id_fkey",
        "commentaries",
        "commentaries",
        ["commentary_id"],
        ["id"],
    )
    op.create_foreign_key(
        "commentaries_post_id_fkey",
        "commentaries",
        "posts",
        ["post_id"],
        ["id"],
    )
    op.create_foreign_key(
        "commentaries_artist_id_fkey",
        "commentaries",
        "artists",
        ["artist_id"],
        ["id"],
    )
