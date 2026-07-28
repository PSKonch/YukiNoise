from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PlaybackContextType(StrEnum):
    TRACK = "track"
    RELEASE = "release"
    PLAYLIST = "playlist"


class RepeatMode(StrEnum):
    OFF = "off"
    TRACK = "track"
    CONTEXT = "context"


class PlaybackContext(BaseModel):
    type: PlaybackContextType
    id: UUID


class PlaybackPlayRequest(BaseModel):
    device_id: UUID
    context: PlaybackContext | None = None
    offset_track_id: UUID | None = None
    position_ms: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_new_context(self) -> "PlaybackPlayRequest":
        if self.context is None and self.offset_track_id is not None:
            raise ValueError("offset_track_id requires context")
        return self


class DeviceRequest(BaseModel):
    device_id: UUID


class PlaybackNextRequest(DeviceRequest):
    ended: bool = False


class PlaybackSeekRequest(DeviceRequest):
    position_ms: int = Field(ge=0)


class PlaybackRepeatRequest(DeviceRequest):
    mode: RepeatMode


class PlaybackProgressRequest(DeviceRequest):
    session_id: UUID
    attempt_id: UUID
    sequence: int = Field(ge=1)
    position_ms: int = Field(ge=0)


class PlaybackTrack(BaseModel):
    id: UUID
    title: str
    duration_ms: int
    stream_url: str


class PlaybackStateResponse(BaseModel):
    session_id: UUID
    revision: int
    active_device_id: UUID
    context: PlaybackContext
    current_track: PlaybackTrack
    current_index: int
    queue_length: int
    attempt_id: UUID
    heartbeat_sequence: int
    position_ms: int
    is_playing: bool
    repeat_mode: RepeatMode
    listened_ms: int
    counted: bool


class PlaybackQueueResponse(BaseModel):
    current_index: int
    tracks: list[PlaybackTrack]


class WebSocketAuthMessage(BaseModel):
    type: str
    access_token: str
    device_id: UUID
