import asyncio
from collections.abc import Awaitable, Callable
from typing import cast
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from redis.exceptions import RedisError

from yn.modules.playback.repository import PlaybackRepository
from yn.shared.settings import settings


def test_redis_compare_and_set_and_ttl() -> None:
    async def scenario() -> None:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        user_id = uuid4()
        repository = PlaybackRepository(client)
        try:
            try:
                await cast(Awaitable[bool], client.ping())
            except RedisError:
                pytest.skip("Redis is not available")

            assert await repository.compare_and_set(user_id, -1, {"revision": 1})
            assert not await repository.compare_and_set(user_id, -1, {"revision": 2})
            assert await repository.compare_and_set(user_id, 1, {"revision": 2})
            assert await repository.get(user_id) == {"revision": 2}
            ttl = await client.ttl(repository._key(user_id))
            assert 0 < ttl <= repository.ttl_seconds
        finally:
            try:
                await repository.delete(user_id)
            except RedisError:
                pass
            close = cast(Callable[[], Awaitable[None]], client.aclose)
            await close()

    asyncio.run(scenario())
