from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrackBase(BaseModel):
    title: str
    genres: list[str] = Field(default_factory=list)


class TrackCreate(TrackBase):
    album_id: UUID


class TrackRead(TrackBase):
    id: UUID
    album_id: UUID
    duration_seconds: int
    path: str
    created_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
