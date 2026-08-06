from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from yn.modules.likes.enums import TargetType

LIKES_EVENTS_TOPIC = "likes.events"


def like_target_key(target_type: TargetType, target_id: UUID) -> str:
    return f"{target_type}:{target_id}"


class LikeCreatedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["like.created"] = "like.created"
    version: Literal[1] = 1
    like_id: UUID
    artist_id: UUID
    target_type: TargetType
    target_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LikeDeletedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["like.deleted"] = "like.deleted"
    version: Literal[1] = 1
    like_id: UUID
    artist_id: UUID
    target_type: TargetType
    target_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
