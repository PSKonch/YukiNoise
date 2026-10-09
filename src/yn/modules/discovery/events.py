from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork

DISCOVERY_EVENTS_TOPIC = "discovery.events"


class TrackIndexRequestedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["track.index_requested"] = "track.index_requested"
    version: Literal[1] = 1
    track_id: UUID


class ReleaseIndexRequestedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["release.index_requested"] = "release.index_requested"
    version: Literal[1] = 1
    release_id: UUID


class ArtistIndexRequestedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["artist.index_requested"] = "artist.index_requested"
    version: Literal[1] = 1
    artist_id: UUID


IndexRequestedEvent = (
    TrackIndexRequestedEvent | ReleaseIndexRequestedEvent | ArtistIndexRequestedEvent
)
IndexScope = Literal["release", "artist"]


async def _request_index(
    uow: UnitOfWork, event: IndexRequestedEvent, source_id: UUID
) -> None:
    if not settings.discovery_enabled:
        return
    await uow.outbox.add(
        event_id=event.event_id,
        topic=DISCOVERY_EVENTS_TOPIC,
        message_key=str(source_id),
        event_type=event.event_type,
        version=event.version,
        payload=event.model_dump(mode="json"),
    )


async def request_track_index(uow: UnitOfWork, track_id: UUID) -> None:
    await _request_index(uow, TrackIndexRequestedEvent(track_id=track_id), track_id)


async def request_release_index(uow: UnitOfWork, release_id: UUID) -> None:
    await _request_index(
        uow, ReleaseIndexRequestedEvent(release_id=release_id), release_id
    )


async def request_artist_index(uow: UnitOfWork, artist_id: UUID) -> None:
    await _request_index(uow, ArtistIndexRequestedEvent(artist_id=artist_id), artist_id)
