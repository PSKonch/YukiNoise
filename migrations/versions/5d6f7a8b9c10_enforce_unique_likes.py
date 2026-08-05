"""enforce unique likes and cascade artist deletion

Revision ID: 5d6f7a8b9c10
Revises: 42a6b8d0c1e3
"""

from typing import Sequence, Union

from alembic import op

revision: str = "5d6f7a8b9c10"
down_revision: Union[str, Sequence[str], None] = "42a6b8d0c1e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_likes_artist_target",
        "likes",
        ["artist_id", "target_type", "target_id"],
    )
    op.drop_constraint("likes_artist_id_fkey", "likes", type_="foreignkey")
    op.create_foreign_key(
        "likes_artist_id_fkey",
        "likes",
        "artists",
        ["artist_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("likes_artist_id_fkey", "likes", type_="foreignkey")
    op.create_foreign_key(
        "likes_artist_id_fkey",
        "likes",
        "artists",
        ["artist_id"],
        ["id"],
    )
    op.drop_constraint("uq_likes_artist_target", "likes", type_="unique")
