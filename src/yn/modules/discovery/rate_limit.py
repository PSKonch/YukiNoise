from collections.abc import Awaitable
from typing import cast
from uuid import UUID

from redis.exceptions import RedisError

from yn.modules.discovery.errors import DiscoveryProviderUnavailableError
from yn.shared.cache.redis_cache import RedisCache
from yn.shared.errors import AppError

RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


class DiscoveryRateLimitError(AppError):
    status_code = 429
    code = "discovery_rate_limit"
    detail = "Too many discovery requests"
    headers = {"Retry-After": "60"}


class DiscoveryRateLimiter:
    def __init__(self, cache: RedisCache, *, limit: int = 10) -> None:
        self._cache = cache
        self._limit = limit

    async def check(self, user_id: UUID) -> None:
        redis = self._cache.client.redis_client
        try:
            count = await cast(
                Awaitable[int],
                redis.eval(RATE_LIMIT_SCRIPT, 1, f"discovery:rate:{user_id}", 60),
            )
        except RedisError as exc:
            raise DiscoveryProviderUnavailableError from exc
        if count > self._limit:
            raise DiscoveryRateLimitError
