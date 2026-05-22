"""profiles search_vector english + russian

Revision ID: c9a7b6d5e4f3
Revises: 70cc60fa4bdc
Create Date: 2026-05-22 20:10:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9a7b6d5e4f3"
down_revision: Union[str, Sequence[str], None] = "70cc60fa4bdc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add combined english+russian search_vector and index."""
    # add new column
    op.execute(
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS search_vector_en_ru tsvector;"
    )

    # populate new column from displayed_name and bio using english+russian configs
    op.execute(
        """
        UPDATE profiles
        SET search_vector_en_ru =
          setweight(to_tsvector('english', coalesce(displayed_name, '')), 'A') ||
          setweight(to_tsvector('english', coalesce(bio, '')), 'B') ||
          setweight(to_tsvector('russian', coalesce(displayed_name, '')), 'A') ||
          setweight(to_tsvector('russian', coalesce(bio, '')), 'B');
        """
    )

    # create index on new column concurrently and perform non-transactional index operations
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_profiles_search_vector_en_ru ON profiles USING GIN (search_vector_en_ru);"
        )
        # drop old index if exists, drop old column, and rename new into place
        op.execute("DROP INDEX IF EXISTS ix_profiles_search_vector;")
        op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS search_vector;")
        op.execute(
            "ALTER TABLE profiles RENAME COLUMN search_vector_en_ru TO search_vector;"
        )
        op.execute(
            "ALTER INDEX IF EXISTS ix_profiles_search_vector_en_ru RENAME TO ix_profiles_search_vector;"
        )


def downgrade() -> None:
    """Downgrade schema: restore english-only search_vector."""
    # add an english-only column
    op.execute(
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS search_vector_en tsvector;"
    )

    # populate english-only vector
    op.execute(
        """
        UPDATE profiles
        SET search_vector_en =
          setweight(to_tsvector('english', coalesce(displayed_name, '')), 'A') ||
          setweight(to_tsvector('english', coalesce(bio, '')), 'B');
        """
    )

    # create index on english-only vector concurrently and swap back in an autocommit block
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_profiles_search_vector_en ON profiles USING GIN (search_vector_en);"
        )
        # drop current combined index/column and restore names
        op.execute("DROP INDEX IF EXISTS ix_profiles_search_vector;")
        op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS search_vector;")
        op.execute(
            "ALTER TABLE profiles RENAME COLUMN search_vector_en TO search_vector;"
        )
        op.execute(
            "ALTER INDEX IF EXISTS ix_profiles_search_vector_en RENAME TO ix_profiles_search_vector;"
        )
