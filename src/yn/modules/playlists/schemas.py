from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from yn.modules.playlists.enums import PlaylistType
from yn.modules.tracks.schemas import TrackRead


class PlaylistCreate(BaseModel):
    title: str
    description: str | None = None
    cover_url: str | None = None
    is_private: bool = False


class PlaylistRead(PlaylistCreate):
    id: UUID
    artist_id: UUID | None
    playlist_type: PlaylistType = PlaylistType.USER
    system_key: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PlaylistUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    cover_url: str | None = None
    is_private: bool | None = None


class PlaylistTrackRead(BaseModel):
    playlist_id: UUID
    track_id: UUID
    added_at: datetime | None = None
    position: int = 0
    track: TrackRead | None = None

    model_config = ConfigDict(from_attributes=True)
