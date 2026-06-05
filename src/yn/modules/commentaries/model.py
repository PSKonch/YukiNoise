from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import UUID as SA_UUID
from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yn.shared.database import Base

if TYPE_CHECKING:
    from yn.modules.artists.model import Artist
    from yn.modules.posts.model import Post


class Commentary(Base):
    __tablename__ = "commentaries"
    __table_args__ = (
        Index("ix_commentaries_post_id_created_at", "post_id", "created_at"),
    )

    id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    artist_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("artists.id"),
        nullable=False,
    )
    post_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("posts.id"),
        nullable=False,
    )
    commentary_id: Mapped[PyUUID | None] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("commentaries.id"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # relationships
    artist: Mapped["Artist"] = relationship("Artist", back_populates="commentaries")
    post: Mapped["Post"] = relationship("Post", back_populates="commentaries")
    parent_commentary: Mapped["Commentary"] = relationship(
        "Commentary", remote_side="Commentary.id", back_populates="child_commentaries"
    )
    child_commentaries: Mapped[list["Commentary"]] = relationship(
        "Commentary",
        remote_side="Commentary.commentary_id",
        back_populates="parent_commentary",
    )
