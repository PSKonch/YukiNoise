from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import UUID as SA_UUID
from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yn.modules.likes.enums import TargetType
from yn.shared.database import Base

if TYPE_CHECKING:
    from yn.modules.artists.model import Artist


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (
        Index("ix_likes_artist_id", "artist_id"),
        Index("ix_likes_target_type_target_id", "target_type", "target_id"),
        Index("ix_likes_created_at", "created_at"),
    )

    id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    artist_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("artists.id"),
        nullable=False,
    )
    target_type: Mapped[TargetType] = mapped_column(nullable=False)
    target_id: Mapped[PyUUID] = mapped_column(SA_UUID(as_uuid=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # relationships
    artist: Mapped["Artist"] = relationship("Artist", back_populates="likes")
