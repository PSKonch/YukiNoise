"""track number unique per release

Revision ID: 6d2b1a9c4f70
Revises: b4c8c537fcf9
Create Date: 2026-05-24 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6d2b1a9c4f70"
down_revision: Union[str, Sequence[str], None] = "b4c8c537fcf9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "uq_tracks_release_track_number_active",
        "tracks",
        ["release_id", "track_number_in_release"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_tracks_release_track_number_active",
        table_name="tracks",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
