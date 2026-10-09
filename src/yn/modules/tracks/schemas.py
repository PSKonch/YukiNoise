from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrackBase(BaseModel):
    title: str
    track_number_in_release: int = Field(ge=1)
    genres: list[str] = Field(default_factory=list)


class TrackCreate(TrackBase):
    release_id: UUID
    featured_artist_ids: list[UUID] = Field(default_factory=list)


class TrackUpdate(BaseModel):
    title: str | None = None
    track_number_in_release: int | None = Field(default=None, ge=1)
    genres: list[str] | None = None
    featured_artist_ids: list[UUID] | None = None


class FeaturedArtistRead(BaseModel):
    id: UUID
    displayed_name: str

    model_config = ConfigDict(from_attributes=True)


class TrackRead(TrackBase):
    id: UUID
    release_id: UUID
    duration_seconds: int
    path: str
    featured_artists: list[FeaturedArtistRead] = Field(default_factory=list)
    created_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TrackUploadAccepted(TrackBase):
    track_id: UUID
    release_id: UUID
    featured_artist_ids: list[UUID] = Field(default_factory=list)
    status: str = "queued"

    model_config = ConfigDict(from_attributes=True)
