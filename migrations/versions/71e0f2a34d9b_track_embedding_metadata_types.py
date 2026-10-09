"""Use numeric document versions and timezone-aware index timestamps.

Revision ID: 71e0f2a34d9b
Revises: 32bc8faa1b0f
"""

import sqlalchemy as sa
from alembic import op

revision: str = "71e0f2a34d9b"
down_revision: str = "32bc8faa1b0f"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column(
        "track_embedding",
        "document_text",
        existing_type=sa.String(),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "track_embedding",
        "document_schema_version",
        existing_type=sa.String(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="document_schema_version::integer",
    )
    op.alter_column("track_embedding", "indexed_at", server_default=None)
    op.alter_column(
        "track_embedding",
        "indexed_at",
        existing_type=sa.String(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="indexed_at::timestamptz",
        server_default=sa.text("now()"),
    )
    op.create_check_constraint(
        "ck_track_embedding_dimension", "track_embedding", "embedding_dimension = 768"
    )


def downgrade() -> None:
    op.drop_constraint("ck_track_embedding_dimension", "track_embedding", type_="check")
    op.alter_column("track_embedding", "indexed_at", server_default=None)
    op.alter_column(
        "track_embedding",
        "indexed_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.String(),
        existing_nullable=False,
        postgresql_using="indexed_at::text",
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "track_embedding",
        "document_schema_version",
        existing_type=sa.Integer(),
        type_=sa.String(),
        existing_nullable=False,
        postgresql_using="document_schema_version::text",
    )
    op.alter_column(
        "track_embedding", "document_text", existing_type=sa.Text(), type_=sa.String()
    )
