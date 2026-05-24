"""merge heads: 6d2b1a9c4f70 and ff2d3c4b5a6e

Revision ID: 8b551fc3adcd
Revises: 6d2b1a9c4f70, ff2d3c4b5a6e
Create Date: 2026-05-24 21:37:29.149033

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "8b551fc3adcd"
down_revision: Union[str, Sequence[str], None] = ("6d2b1a9c4f70", "ff2d3c4b5a6e")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
