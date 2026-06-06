from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from yn.modules.tracks.model import Track


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
        )


@dataclass
class TrackUploadQueuedDTO:
    track_id: UUID
    release_id: UUID
    title: str
    track_number_in_release: int
    status: str = "queued"
