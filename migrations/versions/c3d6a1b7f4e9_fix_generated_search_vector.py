"""fix generated search_vector columns

Revision ID: c3d6a1b7f4e9
Revises: b24ae27f9fe8
Create Date: 2026-05-23 02:25:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d6a1b7f4e9"
down_revision: Union[str, Sequence[str], None] = "b24ae27f9fe8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_profiles_search_vector;")
    op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS search_vector;")
    op.execute(
        """
        ALTER TABLE profiles
        ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (
          setweight(to_tsvector('english', coalesce(displayed_name, '')), 'A') ||
          setweight(to_tsvector('english', coalesce(bio, '')), 'B') ||
          setweight(to_tsvector('russian', coalesce(displayed_name, '')), 'A') ||
          setweight(to_tsvector('russian', coalesce(bio, '')), 'B')
        ) STORED;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_profiles_search_vector ON profiles USING GIN (search_vector);"
    )

    op.execute("DROP INDEX IF EXISTS ix_posts_search_vector;")
    op.execute("ALTER TABLE posts DROP COLUMN IF EXISTS search_vector;")
    op.execute(
        """
        ALTER TABLE posts
        ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (
          setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
          setweight(to_tsvector('english', coalesce(content, '')), 'B') ||
          setweight(to_tsvector('russian', coalesce(title, '')), 'A') ||
          setweight(to_tsvector('russian', coalesce(content, '')), 'B')
        ) STORED;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_posts_search_vector ON posts USING GIN (search_vector);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_profiles_search_vector;")
    op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS search_vector;")
    op.execute("ALTER TABLE profiles ADD COLUMN search_vector tsvector;")
    op.execute(
        """
        UPDATE profiles
        SET search_vector =
          setweight(to_tsvector('english', coalesce(displayed_name, '')), 'A') ||
          setweight(to_tsvector('english', coalesce(bio, '')), 'B') ||
          setweight(to_tsvector('russian', coalesce(displayed_name, '')), 'A') ||
          setweight(to_tsvector('russian', coalesce(bio, '')), 'B');
        """
    )
    op.execute("ALTER TABLE profiles ALTER COLUMN search_vector SET NOT NULL;")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_profiles_search_vector ON profiles USING GIN (search_vector);"
    )

    op.execute("DROP INDEX IF EXISTS ix_posts_search_vector;")
    op.execute("ALTER TABLE posts DROP COLUMN IF EXISTS search_vector;")
    op.execute("ALTER TABLE posts ADD COLUMN search_vector tsvector;")
    op.execute(
        """
        UPDATE posts
        SET search_vector =
          setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
          setweight(to_tsvector('english', coalesce(content, '')), 'B') ||
          setweight(to_tsvector('russian', coalesce(title, '')), 'A') ||
          setweight(to_tsvector('russian', coalesce(content, '')), 'B');
        """
    )
    op.execute("ALTER TABLE posts ALTER COLUMN search_vector SET NOT NULL;")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_posts_search_vector ON posts USING GIN (search_vector);"
    )
