"""merge heads: 03aaa0e2cdfd and eeee41b00107

Revision ID: 70cc60fa4bdc
Revises: 03aaa0e2cdfd, eeee41b00107
Create Date: 2026-05-22 19:59:39.238615

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "70cc60fa4bdc"
down_revision: Union[str, Sequence[str], None] = ("03aaa0e2cdfd", "eeee41b00107")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
