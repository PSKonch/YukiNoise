from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from yn.shared.unit_of_work import UnitOfWork

DISCOVERY_EVENTS_TOPIC = "discovery.events"


class TrackIndexRequestedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["track.index_requested"] = "track.index_requested"
    version: Literal[1] = 1
    track_id: UUID


async def request_track_index(uow: UnitOfWork, track_id: UUID) -> None:
    event = TrackIndexRequestedEvent(track_id=track_id)
    await uow.outbox.add(
        event_id=event.event_id,
        topic=DISCOVERY_EVENTS_TOPIC,
        message_key=str(track_id),
        event_type=event.event_type,
        version=event.version,
        payload=event.model_dump(mode="json"),
    )
