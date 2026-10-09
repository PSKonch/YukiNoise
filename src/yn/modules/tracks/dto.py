from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from yn.modules.artists.model import Artist
    from yn.modules.tracks.model import Track


@dataclass
class FeaturedArtistDTO:
    id: UUID
    displayed_name: str

    @classmethod
    def from_orm(cls, artist: "Artist") -> "FeaturedArtistDTO":
        return cls(id=artist.id, displayed_name=artist.displayed_name)


@dataclass
class TrackDTO:
    id: UUID
    release_id: UUID
    title: str
    duration_seconds: int
    track_number_in_release: int
    path: str
    mime_type: str | None
    genres: list[str]
    created_at: datetime | None
    deleted_at: datetime | None
    featured_artists: list[FeaturedArtistDTO] = field(default_factory=list)

    @classmethod
    def from_orm(cls, track: "Track") -> "TrackDTO":
        return cls(
            id=track.id,
            release_id=track.release_id,
            title=track.title,
            duration_seconds=track.duration_seconds,
            track_number_in_release=track.track_number_in_release,
            path=track.path,
            mime_type=getattr(track, "mime_type", None),
            genres=track.genres,
            created_at=getattr(track, "created_at", None),
            deleted_at=getattr(track, "deleted_at", None),
            featured_artists=[
                FeaturedArtistDTO.from_orm(artist)
                for artist in getattr(track, "featured_artists", [])
                if artist.deleted_at is None
            ],
        )


@dataclass
class TrackUploadQueuedDTO:
    track_id: UUID
    release_id: UUID
    title: str
    track_number_in_release: int
    featured_artist_ids: list[UUID] = field(default_factory=list)
    status: str = "queued"
