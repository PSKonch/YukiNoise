from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from yn.modules.playlists.enums import PlaylistType


class PlaylistCreate(BaseModel):
    title: str
    description: str | None = None
    cover_url: str | None = None
    is_private: bool = False


class PlaylistRead(PlaylistCreate):
    id: UUID
    artist_id: UUID
    playlist_type: PlaylistType = PlaylistType.USER
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PlaylistTrackRead(BaseModel):
    playlist_id: UUID
    track_id: UUID
    added_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
