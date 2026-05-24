from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import UUID as SA_UUID
from sqlalchemy import Computed, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yn.shared.database import Base

if TYPE_CHECKING:
    from yn.modules.posts.model import Post
    from yn.modules.releases.model import Release
    from yn.modules.users.model import User


class Artist(Base):
    __tablename__ = "artists"
    __table_args__ = (
        Index("ix_artists_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_artists_created_at", "created_at", postgresql_using="btree"),
        Index("ix_artists_deleted_at", "deleted_at", postgresql_using="btree"),
        Index(
            "ix_artists_displayed_name_trgm",
            "displayed_name",
            postgresql_using="gin",
            postgresql_ops={"displayed_name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    displayed_name: Mapped[str] = mapped_column(unique=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(nullable=True)
    search_vector: Mapped[TSVECTOR] = mapped_column(
        TSVECTOR,
        Computed(
            """
            setweight(to_tsvector('english', coalesce(displayed_name, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(bio, '')), 'B') ||
            setweight(to_tsvector('russian', coalesce(displayed_name, '')), 'A') ||
            setweight(to_tsvector('russian', coalesce(bio, '')), 'B')
            """,
            persisted=True,
        ),
        nullable=False,
    )

    social_links: Mapped[dict[str, str] | None] = mapped_column(
        JSONB, nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # relationships
    user: Mapped["User"] = relationship("User", back_populates="artist")
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="artist")
    releases: Mapped[list["Release"]] = relationship("Release", back_populates="artist")
