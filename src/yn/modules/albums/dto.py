from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from yn.modules.tracks.dto import TrackDTO

if TYPE_CHECKING:
    from yn.modules.albums.model import Album


@dataclass
class AlbumDTO:
    id: UUID
    profile_id: UUID
    title: str
    description: str | None
    picture_path: str | None
    created_at: datetime | None
    updated_at: datetime | None
    deleted_at: datetime | None

    @classmethod
    def from_orm(cls, album: "Album") -> "AlbumDTO":
        return cls(
            id=album.id,
            profile_id=album.profile_id,
            title=album.title,
            description=getattr(album, "description", None),
            picture_path=getattr(album, "picture_path", None),
            created_at=getattr(album, "created_at", None),
            updated_at=getattr(album, "updated_at", None),
            deleted_at=getattr(album, "deleted_at", None),
        )


@dataclass
class AlbumWithTracksAndAuthorDTO:
    id: UUID
    profile_id: UUID
    title: str
    description: str | None
    picture_path: str | None
    author_name: str | None
    tracks: list[TrackDTO]
    created_at: datetime | None
    updated_at: datetime | None
    deleted_at: datetime | None

    @classmethod
    def from_orm(cls, album: "Album") -> "AlbumWithTracksAndAuthorDTO":
        profile = album.__dict__.get("profile")
        tracks = [
            TrackDTO.from_orm(track) for track in album.__dict__.get("tracks", [])
        ]

        return cls(
            id=album.id,
            profile_id=album.profile_id,
            title=album.title,
            description=getattr(album, "description", None),
            picture_path=getattr(album, "picture_path", None),
            author_name=getattr(profile, "displayed_name", None),
            tracks=tracks,
            created_at=getattr(album, "created_at", None),
            updated_at=getattr(album, "updated_at", None),
            deleted_at=getattr(album, "deleted_at", None),
        )
