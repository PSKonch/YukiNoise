from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import UUID as SA_UUID
from sqlalchemy import Enum, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yn.modules.playlists.enums import PlaylistType
from yn.shared.database import Base

if TYPE_CHECKING:
    from yn.modules.artists.model import Artist
    from yn.modules.tracks.model import Track


class Playlist(Base):
    __tablename__ = "playlists"
    __table_args__ = (
        Index(
            "uq_playlists_artist_system_title",
            "artist_id",
            "title",
            unique=True,
            postgresql_where=text("playlist_type = 'SYSTEM'"),
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    artist_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("artists.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    is_private: Mapped[bool] = mapped_column(nullable=False, default=False)
    playlist_type: Mapped[PlaylistType] = mapped_column(
        Enum(PlaylistType, name="playlist_type"),
        nullable=False,
        default=PlaylistType.USER,
    )

    cover_url: Mapped[str | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # relationships
    artist: Mapped["Artist"] = relationship("Artist", back_populates="playlists")
    tracks: Mapped[list["PlaylistTrack"]] = relationship(
        "PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan"
    )


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"
    __table_args__ = (
        Index("ix_playlist_tracks_playlist_id_added_at", "playlist_id", "added_at"),
    )

    playlist_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("playlists.id", ondelete="CASCADE"),
        primary_key=True,
    )
    track_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # relationships
    playlist: Mapped["Playlist"] = relationship("Playlist", back_populates="tracks")
    track: Mapped["Track"] = relationship("Track", back_populates="playlists")
