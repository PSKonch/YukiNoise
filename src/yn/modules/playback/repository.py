import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, cast
from uuid import UUID

from redis.asyncio import Redis

_CAS_SCRIPT = """
local current = redis.call('GET', KEYS[1])
if not current then
  if tonumber(ARGV[1]) ~= -1 then return 0 end
else
  local decoded = cjson.decode(current)
  if tonumber(decoded.revision) ~= tonumber(ARGV[1]) then return 0 end
end
redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
redis.call('PUBLISH', KEYS[2], ARGV[2])
return 1
"""


class PlaybackRepository:
    ttl_seconds = 7 * 24 * 60 * 60

    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client

    @staticmethod
    def _key(user_id: UUID) -> str:
        return f"playback:v2:{user_id}"

    @staticmethod
    def _channel(user_id: UUID) -> str:
        return f"playback:v2:events:{user_id}"

    async def get(self, user_id: UUID) -> dict[str, Any] | None:
        raw = await cast(
            Awaitable[str | None], self.redis_client.get(self._key(user_id))
        )
        return json.loads(raw) if raw else None

    async def compare_and_set(
        self, user_id: UUID, expected_revision: int, state: dict[str, Any]
    ) -> bool:
        result = await cast(
            Awaitable[int],
            self.redis_client.eval(
                _CAS_SCRIPT,
                2,
                self._key(user_id),
                self._channel(user_id),
                expected_revision,
                json.dumps(state, separators=(",", ":")),
                self.ttl_seconds,
            ),
        )
        return bool(result)

    async def delete(self, user_id: UUID) -> bool:
        deleted = await cast(
            Awaitable[int], self.redis_client.delete(self._key(user_id))
        )
        if deleted:
            await self.redis_client.publish(
                self._channel(user_id), json.dumps({"type": "stopped"})
            )
        return bool(deleted)

    async def subscribe(self, user_id: UUID) -> AsyncIterator[str]:
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(self._channel(user_id))
        try:
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    yield cast(str, message["data"])
        finally:
            await pubsub.unsubscribe(self._channel(user_id))
            close = cast(Callable[[], Awaitable[None]], pubsub.aclose)
            await close()
