import json
from typing import Any

from yn.shared.redis_manager import RedisManager

_redis_cache: "RedisCache | None" = None


class RedisCache:
    def __init__(self, redis_manager: RedisManager) -> None:
        self.client = redis_manager

    def _get_key(self, module: str, key: str) -> str:
        return f"cache:{module}:{key}"

    async def get(self, module: str, key: str) -> dict[str, Any] | None:
        result = await self.client.redis_client.get(self._get_key(module, key))

        if result is None:
            return None

        value = json.loads(result)
        if not isinstance(value, dict):
            raise ValueError("Cached value must be a JSON object")
        return value

    async def set(
        self, module: str, key: str, value: dict[str, Any], expire: int
    ) -> None:
        if expire <= 0:
            raise ValueError("Cache expiration must be positive")

        await self.client.redis_client.set(
            self._get_key(module, key), json.dumps(value, ensure_ascii=False), ex=expire
        )

    async def delete(self, module: str, key: str) -> None:
        await self.client.redis_client.delete(self._get_key(module, key))


def set_redis_cache(cache: RedisCache | None) -> None:
    global _redis_cache
    _redis_cache = cache


def get_redis_cache() -> RedisCache:
    if _redis_cache is None:
        raise RuntimeError("Redis cache not initialized")
    return _redis_cache
