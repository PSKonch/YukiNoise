from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FollowRead(BaseModel):
    id: UUID
    follower_id: UUID
    followed_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FollowStatus(BaseModel):
    is_following: bool
