import json

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractConnection,
    AbstractExchange,
)

from yn.modules.artists.rmq.events import ARTIST_EVENTS_EXCHANGE
from yn.shared.outbox.model import OutboxMessage


class ArtistEventsProducer:
    def __init__(self, url: str, publish_timeout: float = 5.0) -> None:
        self._url = url
        self._publish_timeout = publish_timeout
        self._connection: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange: AbstractExchange | None = None

    async def start(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel(publisher_confirms=True)
        self._exchange = await self._channel.declare_exchange(
            ARTIST_EVENTS_EXCHANGE,
            ExchangeType.DIRECT,
            durable=True,
        )

    async def publish(self, event: OutboxMessage) -> None:
        if self._exchange is None:
            raise RuntimeError("Artist events producer is not started")

        await self._exchange.publish(
            Message(
                body=json.dumps(event.payload, separators=(",", ":")).encode(),
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
                message_id=str(event.id),
                type=event.event_type,
                timestamp=event.occurred_at,
            ),
            routing_key=event.routing_key,
            timeout=self._publish_timeout,
        )

    async def stop(self) -> None:
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
        self._connection = None
        self._channel = None
        self._exchange = None
