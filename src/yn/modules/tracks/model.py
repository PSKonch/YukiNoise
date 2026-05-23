from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import UUID as SA_UUID
from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yn.shared.database import Base

if TYPE_CHECKING:
    from yn.modules.releases.model import Release


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    release_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("releases.id", ondelete="CASCADE"),
        nullable=False,  # single track must belong to a release
    )
    title: Mapped[str] = mapped_column(nullable=False)
    duration_seconds: Mapped[int] = mapped_column(nullable=False)
    path: Mapped[str] = mapped_column(nullable=False)
    genres: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    release: Mapped["Release"] = relationship("Release", back_populates="tracks")

    __table_args__ = (
        Index("ix_tracks_created_at", "created_at", postgresql_using="btree"),
        Index("ix_tracks_deleted_at", "deleted_at", postgresql_using="btree"),
        Index(
            "ix_tracks_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index(
            "uq_tracks_release_title_active",
            "release_id",
            func.lower(title),
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
    )
