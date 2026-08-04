from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

ARTIST_EVENTS_TOPIC = "artists.events"


class ArtistCreatedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["artist.created"] = "artist.created"
    version: Literal[1] = 1
    artist_id: UUID
    user_id: UUID
    displayed_name: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
