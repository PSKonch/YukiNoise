from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TrackRead(BaseModel):
    id: UUID
    album_id: UUID
    title: str
    duration_seconds: int
    path: str
    genres: list[str]
    created_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AlbumBase(BaseModel):
    title: str
    description: str | None = None
    picture_path: str | None = None


class AlbumCreate(AlbumBase):
    pass


class AlbumUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    picture_path: str | None = None


class AlbumRead(AlbumBase):
    id: UUID
    profile_id: UUID
    status: str
    release_date: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AlbumPictureUploadAccepted(BaseModel):
    album_id: UUID
    status: str = "queued"

    model_config = ConfigDict(from_attributes=True)


class AlbumWithTracksAndAuthorRead(AlbumRead):
    author_name: str | None = None
    tracks: list[TrackRead] = []


class AlbumReleaseSchedule(BaseModel):
    release_date: datetime
