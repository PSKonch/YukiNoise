from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ArtistBase(BaseModel):
    displayed_name: str | None = None
    bio: str | None = None
    social_links: dict[str, str] | None = None


class ArtistCreate(ArtistBase):
    displayed_name: str


class ArtistUpdate(ArtistBase):
    pass


class ArtistRead(ArtistBase):
    id: UUID
    user_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class Artist(ArtistRead):
    pass
