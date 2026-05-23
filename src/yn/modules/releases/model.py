from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import UUID as SA_UUID
from sqlalchemy import ForeignKey, Index, and_, func, or_
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import ColumnElement

from yn.shared.database import Base

if TYPE_CHECKING:
    from yn.modules.profiles.model import Profile
    from yn.modules.tracks.model import Track


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (
        Index("ix_releases_created_at", "created_at", postgresql_using="btree"),
        Index("ix_releases_updated_at", "updated_at", postgresql_using="btree"),
        Index("ix_releases_deleted_at", "deleted_at", postgresql_using="btree"),
        Index("ix_releases_profile_id", "profile_id", postgresql_using="btree"),
        Index("ix_releases_status", "status", postgresql_using="btree"),
        Index(
            "ix_releases_release_date",
            "release_date",
            postgresql_using="btree",
        ),
        Index(
            "ix_releases_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    profile_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    cover_path: Mapped[str | None] = mapped_column(
        nullable=True
    )  # a temporary solution until we have a proper media management system in place

    status: Mapped[str] = mapped_column(
        nullable=False, default="draft"
    )  # draft, scheduled, published, deleted
    release_date: Mapped[datetime | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="releases")
    tracks: Mapped[list["Track"]] = relationship("Track", back_populates="release")

    @classmethod
    def public_visibility_clause(cls) -> ColumnElement[bool]:
        return or_(
            cls.status == "published",
            and_(cls.status == "scheduled", cls.release_date <= func.now()),
        )

    @classmethod
    def publicly_visible_clause(cls) -> ColumnElement[bool]:
        return and_(cls.deleted_at.is_(None), cls.public_visibility_clause())
