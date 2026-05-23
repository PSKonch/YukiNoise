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
    path: str
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
            path=track.path,
            genres=track.genres,
            created_at=getattr(track, "created_at", None),
            deleted_at=getattr(track, "deleted_at", None),
        )


@dataclass
class TrackUploadQueuedDTO:
    track_id: UUID
    release_id: UUID
    title: str
    status: str = "queued"
