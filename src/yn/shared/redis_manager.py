from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis


class RedisManager:
    def __init__(self, redis: Redis) -> None:
        self.redis_client = redis

    async def close(self) -> None:
        await self.redis_client.aclose()

    async def ping(self) -> bool:
        return await cast(Awaitable[bool], self.redis_client.ping())
