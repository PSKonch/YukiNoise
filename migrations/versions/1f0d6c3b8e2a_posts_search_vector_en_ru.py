"""posts search_vector english + russian

Revision ID: 1f0d6c3b8e2a
Revises: c9a7b6d5e4f3
Create Date: 2026-05-22 20:25:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1f0d6c3b8e2a"
down_revision: Union[str, Sequence[str], None] = "c9a7b6d5e4f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: rebuild posts search_vector with english+russian."""
    op.execute(
        "ALTER TABLE posts ADD COLUMN IF NOT EXISTS search_vector_en_ru tsvector;"
    )
    op.execute(
        """
        UPDATE posts
        SET search_vector_en_ru =
          setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
          setweight(to_tsvector('english', coalesce(content, '')), 'B') ||
          setweight(to_tsvector('russian', coalesce(title, '')), 'A') ||
          setweight(to_tsvector('russian', coalesce(content, '')), 'B');
        """
    )

    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_posts_search_vector_en_ru ON posts USING GIN (search_vector_en_ru);"
        )
        op.execute("DROP INDEX IF EXISTS ix_posts_search_vector;")
        op.execute("ALTER TABLE posts DROP COLUMN IF EXISTS search_vector;")
        op.execute(
            "ALTER TABLE posts RENAME COLUMN search_vector_en_ru TO search_vector;"
        )
        op.execute(
            "ALTER INDEX IF EXISTS ix_posts_search_vector_en_ru RENAME TO ix_posts_search_vector;"
        )


def downgrade() -> None:
    """Downgrade schema: restore english-only posts search_vector."""
    op.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS search_vector_en tsvector;")
    op.execute(
        """
        UPDATE posts
        SET search_vector_en =
          setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
          setweight(to_tsvector('english', coalesce(content, '')), 'B');
        """
    )

    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_posts_search_vector_en ON posts USING GIN (search_vector_en);"
        )
        op.execute("DROP INDEX IF EXISTS ix_posts_search_vector;")
        op.execute("ALTER TABLE posts DROP COLUMN IF EXISTS search_vector;")
        op.execute("ALTER TABLE posts RENAME COLUMN search_vector_en TO search_vector;")
        op.execute(
            "ALTER INDEX IF EXISTS ix_posts_search_vector_en RENAME TO ix_posts_search_vector;"
        )
