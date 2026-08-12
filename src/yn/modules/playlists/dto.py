from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from yn.modules.playlists.enums import PlaylistType
from yn.modules.tracks.dto import TrackDTO

if TYPE_CHECKING:
    from yn.modules.playlists.model import Playlist, PlaylistTrack


@dataclass
class PlaylistDTO:
    id: UUID
    artist_id: UUID | None
    title: str
    description: str | None = None
    cover_url: str | None = None
    is_private: bool = False
    playlist_type: PlaylistType = PlaylistType.USER
    system_key: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    @classmethod
    def from_orm(cls, playlist: "Playlist") -> "PlaylistDTO":
        return cls(
            id=playlist.id,
            artist_id=playlist.artist_id,
            title=playlist.title,
            description=playlist.description,
            cover_url=playlist.cover_url,
            is_private=playlist.is_private,
            playlist_type=playlist.playlist_type,
            system_key=playlist.system_key,
            period_start=playlist.period_start,
            period_end=playlist.period_end,
            created_at=getattr(playlist, "created_at", None),
            updated_at=getattr(playlist, "updated_at", None),
            deleted_at=getattr(playlist, "deleted_at", None),
        )


@dataclass
class PlaylistTrackDTO:
    playlist_id: UUID
    track_id: UUID
    added_at: datetime | None = None
    position: int = 0
    track: TrackDTO | None = None

    @classmethod
    def from_orm(cls, playlist_track: "PlaylistTrack") -> "PlaylistTrackDTO":
        track = playlist_track.__dict__.get("track")
        return cls(
            playlist_id=playlist_track.playlist_id,
            track_id=playlist_track.track_id,
            added_at=getattr(playlist_track, "added_at", None),
            position=getattr(playlist_track, "position", 0),
            track=TrackDTO.from_orm(track) if track else None,
        )
