"""tracks album title unique

Revision ID: f0b9c9af1201
Revises: a7233aaf8978
Create Date: 2026-05-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0b9c9af1201"
down_revision: Union[str, Sequence[str], None] = "a7233aaf8978"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY album_id, lower(title)
                    ORDER BY created_at ASC, id ASC
                ) AS rn
            FROM tracks
            WHERE deleted_at IS NULL
        )
        UPDATE tracks AS t
        SET deleted_at = now()
        FROM ranked AS r
        WHERE t.id = r.id
          AND r.rn > 1;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_tracks_album_title_active
        ON tracks (album_id, lower(title))
        WHERE deleted_at IS NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_tracks_album_title_active;")
