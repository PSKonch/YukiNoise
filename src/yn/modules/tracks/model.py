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
    from yn.modules.artists.model import Artist
    from yn.modules.playlists.model import PlaylistTrack
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
    track_number_in_release: Mapped[int] = mapped_column(nullable=False)
    path: Mapped[str] = mapped_column(nullable=False)
    genres: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    play_count: Mapped[int] = mapped_column(nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(nullable=False, default=0)

    bitrate: Mapped[int | None] = mapped_column(nullable=True)
    mime_type: Mapped[str | None] = mapped_column(nullable=True)
    waveform_path: Mapped[str | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    release: Mapped["Release"] = relationship("Release", back_populates="tracks")
    playlists: Mapped[list["PlaylistTrack"]] = relationship(
        "PlaylistTrack", back_populates="track"
    )
    featured_artists: Mapped[list["Artist"]] = relationship(
        "Artist",
        secondary="track_features",
        back_populates="featured_tracks",
        order_by="Artist.displayed_name",
        lazy="selectin",
        passive_deletes=True,
    )

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
        Index(
            "uq_tracks_release_track_number_active",
            "release_id",
            "track_number_in_release",
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
    )


class TrackFeature(Base):
    __tablename__ = "track_features"

    track_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    artist_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("artists.id", ondelete="CASCADE"),
        primary_key=True,
    )

    __table_args__ = (
        Index("ix_track_features_artist_id", "artist_id", postgresql_using="btree"),
    )
