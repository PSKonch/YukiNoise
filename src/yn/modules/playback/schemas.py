from uuid import UUID

from pydantic import BaseModel


class PlaybackStartRequest(BaseModel):
    track_id: UUID


class PlaybackActionRequest(BaseModel):
    pass


class PlaybackSeekRequest(BaseModel):
    position: int


class PlaybackSessionResponse(BaseModel):
    session_id: UUID
    track_id: UUID
    position: int
    duration: int
    is_paused: bool
