"""rename albums to releases

Revision ID: 9b6d7e8f4c21
Revises: 70cc60fa4bdc, b24ae27f9fe8
Create Date: 2026-05-24 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b6d7e8f4c21"
down_revision: Union[str, Sequence[str], None] = ("70cc60fa4bdc", "b24ae27f9fe8")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("albums", "releases")

    op.alter_column(
        "releases",
        "picture_path",
        existing_type=sa.String(),
        new_column_name="cover_path",
    )
    op.alter_column(
        "tracks",
        "album_id",
        existing_type=sa.UUID(),
        new_column_name="release_id",
    )

    op.execute(
        "ALTER TABLE releases RENAME CONSTRAINT albums_profile_id_fkey TO releases_profile_id_fkey;"
    )
    op.execute(
        "ALTER TABLE tracks RENAME CONSTRAINT tracks_album_id_fkey TO tracks_release_id_fkey;"
    )

    op.execute("ALTER INDEX ix_albums_created_at RENAME TO ix_releases_created_at;")
    op.execute("ALTER INDEX ix_albums_updated_at RENAME TO ix_releases_updated_at;")
    op.execute("ALTER INDEX ix_albums_deleted_at RENAME TO ix_releases_deleted_at;")
    op.execute("ALTER INDEX ix_albums_profile_id RENAME TO ix_releases_profile_id;")
    op.execute("ALTER INDEX ix_albums_status RENAME TO ix_releases_status;")
    op.execute("ALTER INDEX ix_albums_release_date RENAME TO ix_releases_release_date;")
    op.execute("ALTER INDEX ix_albums_title_trgm RENAME TO ix_releases_title_trgm;")
    op.execute(
        "ALTER INDEX uq_tracks_album_title_active RENAME TO uq_tracks_release_title_active;"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX uq_tracks_release_title_active RENAME TO uq_tracks_album_title_active;"
    )
    op.execute("ALTER INDEX ix_releases_title_trgm RENAME TO ix_albums_title_trgm;")
    op.execute("ALTER INDEX ix_releases_release_date RENAME TO ix_albums_release_date;")
    op.execute("ALTER INDEX ix_releases_status RENAME TO ix_albums_status;")
    op.execute("ALTER INDEX ix_releases_profile_id RENAME TO ix_albums_profile_id;")
    op.execute("ALTER INDEX ix_releases_deleted_at RENAME TO ix_albums_deleted_at;")
    op.execute("ALTER INDEX ix_releases_updated_at RENAME TO ix_albums_updated_at;")
    op.execute("ALTER INDEX ix_releases_created_at RENAME TO ix_albums_created_at;")

    op.execute(
        "ALTER TABLE tracks RENAME CONSTRAINT tracks_release_id_fkey TO tracks_album_id_fkey;"
    )
    op.execute(
        "ALTER TABLE releases RENAME CONSTRAINT releases_profile_id_fkey TO albums_profile_id_fkey;"
    )

    op.alter_column(
        "tracks",
        "release_id",
        existing_type=sa.UUID(),
        new_column_name="album_id",
    )
    op.alter_column(
        "releases",
        "cover_path",
        existing_type=sa.String(),
        new_column_name="picture_path",
    )

    op.rename_table("releases", "albums")
