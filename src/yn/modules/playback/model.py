from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import UUID as SA_UUID
from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yn.shared.database import Base

if TYPE_CHECKING:
    from yn.modules.tracks.model import Track
    from yn.modules.users.model import User


class PlaybackSessionEvent(Base):
    __tablename__ = "playback_session_events"
    __table_args__ = (
        Index(
            "ix_playback_session_events_user_id", "user_id", postgresql_using="btree"
        ),
        Index(
            "ix_playback_session_events_track_id", "track_id", postgresql_using="btree"
        ),
        Index(
            "ix_playback_session_events_is_active",
            "is_active",
            postgresql_using="btree",
        ),
        Index(
            "ix_playback_session_events_session_id",
            "session_id",
            postgresql_using="btree",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    track_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True), nullable=False, default=uuid4
    )  # it's a lively session identifier, not a foreign key to another table

    position: Mapped[int] = mapped_column(nullable=False, default=0)  # in seconds
    listened_seconds: Mapped[int] = mapped_column(
        nullable=False, default=0
    )  # in seconds
    duration: Mapped[int] = mapped_column(nullable=False, default=0)  # in seconds
    is_paused: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False, onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="playback_sessions")
    track: Mapped["Track"] = relationship("Track", back_populates="playback_sessions")
