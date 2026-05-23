"""merge heads: 0a20dc85a0df and 9b6d7e8f4c21

Revision ID: 2e46a64a7915
Revises: 0a20dc85a0df, 9b6d7e8f4c21
Create Date: 2026-05-24 02:20:53.499693

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "2e46a64a7915"
down_revision: Union[str, Sequence[str], None] = ("0a20dc85a0df", "9b6d7e8f4c21")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
