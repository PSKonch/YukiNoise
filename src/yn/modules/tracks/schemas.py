from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrackBase(BaseModel):
    title: str
    track_number_in_release: int = Field(ge=1)
    genres: list[str] = Field(default_factory=list)


class TrackCreate(TrackBase):
    release_id: UUID


class TrackUpdate(BaseModel):
    title: str | None = None
    track_number_in_release: int | None = Field(default=None, ge=1)
    genres: list[str] | None = None


class TrackRead(TrackBase):
    id: UUID
    release_id: UUID
    duration_seconds: int
    path: str
    created_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TrackUploadAccepted(TrackBase):
    track_id: UUID
    release_id: UUID
    status: str = "queued"

    model_config = ConfigDict(from_attributes=True)
