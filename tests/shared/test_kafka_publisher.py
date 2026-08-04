import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from aiokafka.structs import RecordMetadata
from faststream.kafka import KafkaBroker

from yn.shared.publisher import KafkaPublisher


def test_publish_uses_scoped_topic_and_serializes_key() -> None:
    async def run() -> None:
        broker = AsyncMock(spec=KafkaBroker)
        metadata = MagicMock(spec=RecordMetadata)
        broker.publish.return_value = metadata
        publisher = KafkaPublisher(
            "artists.events",
            broker=cast(KafkaBroker, broker),
        )
        event = {"event_type": "artist.created", "version": 1}
        event_id = uuid4()

        result = await publisher.publish(
            event,
            key=event_id,
            headers={"event-type": "artist.created"},
            correlation_id=str(event_id),
        )

        assert result is metadata
        broker.publish.assert_awaited_once_with(
            event,
            topic="artists.events",
            key=str(event_id).encode(),
            partition=None,
            timestamp_ms=None,
            headers={"event-type": "artist.created"},
            correlation_id=str(event_id),
            no_confirm=False,
        )

    asyncio.run(run())


def test_lifecycle_is_idempotent() -> None:
    async def run() -> None:
        broker = AsyncMock(spec=KafkaBroker)
        publisher = KafkaPublisher(
            "tracks.events",
            broker=cast(KafkaBroker, broker),
        )

        await publisher.start()
        await publisher.start()
        await publisher.stop()
        await publisher.stop()

        broker.start.assert_awaited_once()
        broker.stop.assert_awaited_once()

    asyncio.run(run())


@pytest.mark.parametrize("topic", ["", " ", " artists.events", "artists.events "])
def test_rejects_invalid_topic(topic: str) -> None:
    with pytest.raises(ValueError, match="topic"):
        KafkaPublisher(topic, broker=cast(KafkaBroker, AsyncMock(spec=KafkaBroker)))


def test_idempotence_requires_all_acknowledgements() -> None:
    with pytest.raises(ValueError, match="acks='all'"):
        KafkaPublisher("artists.events", acks=1, enable_idempotence=True)
