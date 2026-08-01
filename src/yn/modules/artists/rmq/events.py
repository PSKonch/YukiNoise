from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

ARTIST_EVENTS_EXCHANGE = "artists.events"
ARTIST_CREATED_QUEUE = "playlists.artist-created"
ARTIST_CREATED_ROUTING_KEY = "artist.created.v1"


class ArtistCreatedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["artist.created"] = "artist.created"
    version: Literal[1] = 1
    artist_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
