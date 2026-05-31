from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from yn.modules.tracks.dto import TrackDTO

if TYPE_CHECKING:
    from yn.modules.releases.model import Release


@dataclass
class ReleaseDTO:
    id: UUID
    artist_id: UUID
    title: str
    description: str | None
    cover_path: str | None
    release_type: str
    status: str
    release_date: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    deleted_at: datetime | None

    @classmethod
    def from_orm(cls, release: "Release") -> "ReleaseDTO":
        return cls(
            id=release.id,
            artist_id=release.artist_id,
            title=release.title,
            release_type=release.release_type,
            description=getattr(release, "description", None),
            cover_path=getattr(release, "cover_path", None),
            status=getattr(release, "status", "draft"),
            release_date=getattr(release, "release_date", None),
            created_at=getattr(release, "created_at", None),
            updated_at=getattr(release, "updated_at", None),
            deleted_at=getattr(release, "deleted_at", None),
        )


@dataclass
class ReleaseWithTracksAndAuthorDTO:
    id: UUID
    artist_id: UUID
    title: str
    description: str | None
    cover_path: str | None
    release_type: str
    status: str
    release_date: datetime | None
    author_name: str | None
    tracks: list[TrackDTO]
    created_at: datetime | None
    updated_at: datetime | None
    deleted_at: datetime | None

    @classmethod
    def from_orm(cls, release: "Release") -> "ReleaseWithTracksAndAuthorDTO":
        artist = release.__dict__.get("artist")
        tracks = [
            TrackDTO.from_orm(track) for track in release.__dict__.get("tracks", [])
        ]

        return cls(
            id=release.id,
            artist_id=release.artist_id,
            title=release.title,
            description=getattr(release, "description", None),
            cover_path=getattr(release, "cover_path", None),
            release_type=release.release_type,
            status=getattr(release, "status", "draft"),
            release_date=getattr(release, "release_date", None),
            author_name=getattr(artist, "displayed_name", None),
            tracks=tracks,
            created_at=getattr(release, "created_at", None),
            updated_at=getattr(release, "updated_at", None),
            deleted_at=getattr(release, "deleted_at", None),
        )
