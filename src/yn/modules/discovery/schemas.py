from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceField = Literal[
    "track.title",
    "track.genres",
    "artist.displayed_name",
    "artist.bio",
    "release.title",
    "release.description",
]


class DiscoverySearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=8, ge=1, le=20)

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value


class CurationPreviewRequest(DiscoverySearchRequest): ...


class SearchTrackRead(BaseModel):
    track_id: UUID
    track_title: str
    artist_name: str
    release_title: str
    distance: float

    model_config = ConfigDict(from_attributes=True)


class GeneratedTrack(BaseModel):
    track_id: UUID
    reason: str = Field(min_length=1, max_length=300)
    sources: list[SourceField] = Field(min_length=1, max_length=6)

    model_config = ConfigDict(extra="forbid")


class GeneratedCuration(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    summary: str = Field(max_length=500)
    tracks: list[GeneratedTrack] = Field(max_length=20)

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def empty(cls) -> "GeneratedCuration":
        return cls(title="Подборка не найдена", summary="", tracks=[])


class CurationPreviewRead(GeneratedCuration):
    pass
