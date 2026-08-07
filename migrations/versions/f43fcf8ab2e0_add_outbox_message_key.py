"""add outbox message key

Revision ID: f43fcf8ab2e0
Revises: 03648cac3bdc
Create Date: 2026-08-07 14:43:32.060299

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f43fcf8ab2e0"
down_revision: Union[str, Sequence[str], None] = "03648cac3bdc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "outbox",
        sa.Column("message_key", sa.String(length=255), nullable=True),
    )
    op.execute("UPDATE outbox SET message_key = payload->>'artist_id'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("outbox", "message_key")
