import asyncio
from typing import Any, Literal
from uuid import UUID

from aiokafka.structs import RecordMetadata
from faststream.kafka import KafkaBroker

from yn.shared.settings import settings

KafkaAck = Literal[0, 1, -1, "all"]
KafkaKey = bytes | bytearray | str | int | UUID


class KafkaPublisher:
    def __init__(
        self,
        topic: str,
        broker: KafkaBroker | None = None,
        *,
        url: str | None = None,
        acks: KafkaAck = "all",
        request_timeout_ms: int = 10_000,
        max_batch_size: int = 16 * 1024,
        linger_ms: int = 5,
        enable_idempotence: bool = True,
    ) -> None:
        if not topic or topic != topic.strip():
            raise ValueError("Kafka topic must be a non-empty, trimmed string")
        if request_timeout_ms <= 0:
            raise ValueError("Kafka request timeout must be positive")
        if max_batch_size <= 0:
            raise ValueError("Kafka max batch size must be positive")
        if linger_ms < 0:
            raise ValueError("Kafka linger must not be negative")
        if enable_idempotence and acks not in (-1, "all"):
            raise ValueError("Idempotent Kafka publisher requires acks='all'")

        self.topic = topic
        self.broker = broker or KafkaBroker(
            bootstrap_servers=url or settings.kafka_url,
            acks=acks,
            request_timeout_ms=request_timeout_ms,
            max_batch_size=max_batch_size,
            linger_ms=linger_ms,
            enable_idempotence=enable_idempotence,
        )
        self._started = False
        self._lifecycle_lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lifecycle_lock:
            if self._started:
                return
            await self.broker.start()
            self._started = True

    async def stop(self) -> None:
        async with self._lifecycle_lock:
            if not self._started:
                return
            await self.broker.stop()
            self._started = False

    async def __aenter__(self) -> "KafkaPublisher":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.stop()

    async def publish(
        self,
        message: Any,
        *,
        key: KafkaKey | None = None,
        partition: int | None = None,
        timestamp_ms: int | None = None,
        headers: dict[str, str] | None = None,
        correlation_id: str | None = None,
    ) -> RecordMetadata:
        return await self.broker.publish(
            message,
            topic=self.topic,
            key=self._encode_key(key),
            partition=partition,
            timestamp_ms=timestamp_ms,
            headers=headers,
            correlation_id=correlation_id,
            no_confirm=False,
        )

    @staticmethod
    def _encode_key(key: KafkaKey | None) -> bytes | None:
        if key is None:
            return None
        if isinstance(key, bytes):
            return key
        if isinstance(key, bytearray):
            return bytes(key)
        return str(key).encode()


kafka_broker = KafkaBroker(
    bootstrap_servers=settings.kafka_url,
    acks="all",
    request_timeout_ms=10_000,
    max_batch_size=16 * 1024,
    linger_ms=5,
    enable_idempotence=True,
)


def get_kafka_publisher(topic: str) -> KafkaPublisher:
    return KafkaPublisher(topic=topic, broker=kafka_broker)
