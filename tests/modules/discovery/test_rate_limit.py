import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from redis.exceptions import RedisError

from yn.modules.discovery.errors import DiscoveryProviderUnavailableError
from yn.modules.discovery.rate_limit import (
    DiscoveryRateLimiter,
    DiscoveryRateLimitError,
)
from yn.shared.cache.redis_cache import RedisCache


def test_rate_limit_allows_ten_requests_and_rejects_the_next() -> None:
    async def run() -> None:
        redis = SimpleNamespace(eval=AsyncMock(side_effect=range(1, 12)))
        cache = cast(
            RedisCache, SimpleNamespace(client=SimpleNamespace(redis_client=redis))
        )
        limiter = DiscoveryRateLimiter(cache)
        user_id = uuid4()
        for _ in range(10):
            await limiter.check(user_id)
        with pytest.raises(DiscoveryRateLimitError) as caught:
            await limiter.check(user_id)
        assert caught.value.status_code == 429
        assert caught.value.headers == {"Retry-After": "60"}
        assert redis.eval.await_args.args[1:] == (1, f"discovery:rate:{user_id}", 60)

    asyncio.run(run())


def test_rate_limit_returns_service_unavailable_when_redis_fails() -> None:
    async def run() -> None:
        redis = SimpleNamespace(eval=AsyncMock(side_effect=RedisError("unavailable")))
        cache = cast(
            RedisCache, SimpleNamespace(client=SimpleNamespace(redis_client=redis))
        )
        with pytest.raises(DiscoveryProviderUnavailableError):
            await DiscoveryRateLimiter(cache).check(uuid4())

    asyncio.run(run())
