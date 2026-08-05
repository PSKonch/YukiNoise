from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from yn.modules.likes.enums import TargetType


class LikeRead(BaseModel):
    id: UUID
    artist_id: UUID
    target_type: TargetType
    target_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LikeStatus(BaseModel):
    is_liked: bool
