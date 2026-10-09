from faststream.kafka import KafkaRouter
from faststream.middlewares import AckPolicy

from yn.modules.discovery.events import (
    DISCOVERY_EVENTS_TOPIC,
    IndexRequestedEvent,
    ReleaseIndexRequestedEvent,
    TrackIndexRequestedEvent,
)
from yn.tasks.index_track import index_source_embeddings, index_track_embedding

router = KafkaRouter()


@router.subscriber(
    DISCOVERY_EVENTS_TOPIC,
    group_id="discovery.indexing.v1",
    auto_offset_reset="earliest",
    ack_policy=AckPolicy.NACK_ON_ERROR,
    no_reply=True,
)
async def consume_track_index_requested(event: IndexRequestedEvent) -> None:
    if isinstance(event, TrackIndexRequestedEvent):
        await index_track_embedding.kiq(str(event.track_id))
    elif isinstance(event, ReleaseIndexRequestedEvent):
        await index_source_embeddings.kiq(str(event.release_id), "release")
    else:
        await index_source_embeddings.kiq(str(event.artist_id), "artist")
