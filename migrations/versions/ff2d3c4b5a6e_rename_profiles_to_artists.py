"""rename profiles to artists

Revision ID: ff2d3c4b5a6e
Revises: f0b9c9af1201
Create Date: 2026-05-24 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "ff2d3c4b5a6e"
down_revision = "f0b9c9af1201"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename main table
    op.execute("ALTER TABLE profiles RENAME TO artists;")

    # Rename indexes on profiles -> artists
    op.execute(
        "ALTER INDEX ix_profiles_search_vector RENAME TO ix_artists_search_vector;"
    )
    op.execute("ALTER INDEX ix_profiles_created_at RENAME TO ix_artists_created_at;")
    op.execute("ALTER INDEX ix_profiles_deleted_at RENAME TO ix_artists_deleted_at;")
    op.execute(
        "ALTER INDEX ix_profiles_displayed_name_trgm RENAME TO ix_artists_displayed_name_trgm;"
    )

    # Rename FK columns and related indexes/constraints in posts
    op.execute("ALTER TABLE posts RENAME COLUMN profile_id TO artist_id;")
    op.execute("ALTER INDEX ix_posts_profile_id RENAME TO ix_posts_artist_id;")
    op.execute(
        "ALTER TABLE posts RENAME CONSTRAINT posts_profile_id_fkey TO posts_artist_id_fkey;"
    )

    # Rename FK columns and related indexes/constraints in releases
    op.execute("ALTER TABLE releases RENAME COLUMN profile_id TO artist_id;")
    op.execute("ALTER INDEX ix_releases_profile_id RENAME TO ix_releases_artist_id;")
    op.execute(
        "ALTER TABLE releases RENAME CONSTRAINT releases_profile_id_fkey TO releases_artist_id_fkey;"
    )


def downgrade() -> None:
    # Downgrade: revert names
    op.execute(
        "ALTER TABLE releases RENAME CONSTRAINT releases_artist_id_fkey TO releases_profile_id_fkey;"
    )
    op.execute("ALTER INDEX ix_releases_artist_id RENAME TO ix_releases_profile_id;")
    op.execute("ALTER TABLE releases RENAME COLUMN artist_id TO profile_id;")

    op.execute(
        "ALTER TABLE posts RENAME CONSTRAINT posts_artist_id_fkey TO posts_profile_id_fkey;"
    )
    op.execute("ALTER INDEX ix_posts_artist_id RENAME TO ix_posts_profile_id;")
    op.execute("ALTER TABLE posts RENAME COLUMN artist_id TO profile_id;")

    op.execute(
        "ALTER INDEX ix_artists_search_vector RENAME TO ix_profiles_search_vector;"
    )
    op.execute("ALTER INDEX ix_artists_created_at RENAME TO ix_profiles_created_at;")
    op.execute("ALTER INDEX ix_artists_deleted_at RENAME TO ix_profiles_deleted_at;")
    op.execute(
        "ALTER INDEX ix_artists_displayed_name_trgm RENAME TO ix_profiles_displayed_name_trgm;"
    )
    op.execute("ALTER TABLE artists RENAME TO profiles;")
