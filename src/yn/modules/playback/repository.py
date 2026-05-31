from collections.abc import Awaitable
from typing import cast
from uuid import UUID

from redis.asyncio import Redis


class PlaybackRepository:
    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client

    @staticmethod
    def _key(user_id: UUID) -> str:
        return f"playback:{user_id}"

    async def get_playback(self, user_id: UUID) -> dict[str, str] | None:
        playback = await cast(
            Awaitable[dict[str, str]], self.redis_client.hgetall(self._key(user_id))
        )
        return playback or None

    async def save_playback(
        self,
        user_id: UUID,
        *,
        session_id: UUID,
        track_id: UUID,
        position: int,
        duration: int,
        updated_at: int,
        is_paused: int,
    ) -> None:
        await cast(
            Awaitable[int],
            self.redis_client.hset(
                self._key(user_id),
                mapping={
                    "session_id": str(session_id),
                    "track_id": str(track_id),
                    "position": position,
                    "duration": duration,
                    "updated_at": updated_at,
                    "is_paused": is_paused,
                },
            ),
        )

    async def delete_playback(self, user_id: UUID) -> None:
        await self.redis_client.delete(self._key(user_id))

    async def exists(self, user_id: UUID) -> bool:
        return (
            await cast(Awaitable[int], self.redis_client.exists(self._key(user_id)))
        ) > 0
