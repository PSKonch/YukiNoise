from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfileBase(BaseModel):
    displayed_name: str | None = None
    bio: str | None = None
    social_links: dict[str, str] | None = None


class ProfileCreate(ProfileBase):
    displayed_name: str


class ProfileUpdate(ProfileBase):
    pass


class ProfileRead(ProfileBase):
    id: UUID
    user_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class Profile(ProfileRead):
    pass
