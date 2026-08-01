import logging

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import (
    AbstractChannel,
    AbstractConnection,
    AbstractIncomingMessage,
    AbstractQueue,
)
from pydantic import ValidationError

from yn.modules.artists.rmq.events import (
    ARTIST_CREATED_QUEUE,
    ARTIST_CREATED_ROUTING_KEY,
    ARTIST_EVENTS_EXCHANGE,
    ArtistCreatedEvent,
)
from yn.modules.playlists.service import PlaylistService
from yn.shared.database import async_primary_session
from yn.shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class ArtistEventsConsumer:
    def __init__(self, url: str, prefetch_count: int = 10) -> None:
        self._url = url
        self._prefetch_count = prefetch_count
        self._connection: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None
        self._queue: AbstractQueue | None = None
        self._consumer_tag: str | None = None

    async def start(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self._prefetch_count)
        exchange = await self._channel.declare_exchange(
            ARTIST_EVENTS_EXCHANGE,
            ExchangeType.DIRECT,
            durable=True,
        )
        self._queue = await self._channel.declare_queue(
            ARTIST_CREATED_QUEUE,
            durable=True,
        )
        await self._queue.bind(exchange, routing_key=ARTIST_CREATED_ROUTING_KEY)
        self._consumer_tag = await self._queue.consume(self._consume)

    async def stop(self) -> None:
        if self._queue is not None and self._consumer_tag is not None:
            await self._queue.cancel(self._consumer_tag)
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
        self._connection = None
        self._channel = None
        self._queue = None
        self._consumer_tag = None

    async def _consume(self, message: AbstractIncomingMessage) -> None:
        try:
            event = ArtistCreatedEvent.model_validate_json(message.body)
        except ValidationError:
            logger.exception("Rejecting invalid artist-created event")
            await message.reject(requeue=False)
            return

        async with message.process(requeue=True):
            await self._create_favs_playlist(event)

    @staticmethod
    async def _create_favs_playlist(event: ArtistCreatedEvent) -> None:
        async with async_primary_session() as session:
            async with UnitOfWork(session) as uow:
                await PlaylistService(uow).create_favs_playlist(event.artist_id)
