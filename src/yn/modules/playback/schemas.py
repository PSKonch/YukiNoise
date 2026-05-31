from uuid import UUID

from pydantic import BaseModel


class PlaybackStartRequest(BaseModel):
    track_id: UUID
    device_id: str | None = (
        None  # for future use, e.g. to specify which output device to use
    )


class PlaybackProgressRequest(BaseModel):
    session_id: UUID
    position: int
    duration: int


class PlaybackActionRequest(BaseModel):
    session_id: UUID
    position: int | None = None  # optional, for pause/resume/stop actions


class PlaybackSessionResponse(BaseModel):
    session_id: UUID
    track_id: UUID
    position: int
    duration: int
    is_paused: bool
    is_active: bool
