from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TrackRead(BaseModel):
    id: UUID
    release_id: UUID
    title: str
    duration_seconds: int
    path: str
    genres: list[str]
    created_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ReleaseBase(BaseModel):
    title: str
    description: str | None = None
    cover_path: str | None = None


class ReleaseCreate(ReleaseBase):
    pass


class ReleaseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    cover_path: str | None = None


class ReleaseRead(ReleaseBase):
    id: UUID
    profile_id: UUID
    status: str
    release_date: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ReleaseCoverUploadAccepted(BaseModel):
    release_id: UUID
    status: str = "queued"

    model_config = ConfigDict(from_attributes=True)


class ReleaseWithTracksAndAuthorRead(ReleaseRead):
    author_name: str | None = None
    tracks: list[TrackRead] = []


class ReleaseSchedule(BaseModel):
    release_date: datetime
