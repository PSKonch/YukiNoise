from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, Field

from yn.shared.unit_of_work import UnitOfWork

RELEASE_EVENTS_TOPIC = "releases.events"


class ReleasePublishedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["release.published"] = "release.published"
    version: Literal[1] = 1
    release_id: UUID
    occurred_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))


async def record_release_published(uow: UnitOfWork, release_id: UUID) -> None:
    event = ReleasePublishedEvent(release_id=release_id)
    await uow.outbox.add(
        event_id=event.event_id,
        topic=RELEASE_EVENTS_TOPIC,
        message_key=str(release_id),
        event_type=event.event_type,
        version=event.version,
        payload=event.model_dump(mode="json"),
    )
