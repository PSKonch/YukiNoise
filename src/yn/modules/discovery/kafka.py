from faststream.kafka import KafkaRouter
from faststream.middlewares import AckPolicy

from yn.modules.discovery.events import DISCOVERY_EVENTS_TOPIC, TrackIndexRequestedEvent
from yn.tasks.index_track import index_track_embedding

router = KafkaRouter()


@router.subscriber(
    DISCOVERY_EVENTS_TOPIC,
    group_id="discovery.indexing.v1",
    auto_offset_reset="earliest",
    ack_policy=AckPolicy.NACK_ON_ERROR,
    no_reply=True,
)
async def consume_track_index_requested(event: TrackIndexRequestedEvent) -> None:
    await index_track_embedding.kiq(str(event.track_id))
