from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from yn.modules.playback.repository import PlaybackRepository
from yn.modules.playback.service import PlaybackService
from yn.modules.tracks.tracks_play_counter_queue import TracksPlayCounterQueue
from yn.shared.database import async_primary_session
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork, get_uow


@lru_cache
def get_playback_redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def get_playback_repository() -> PlaybackRepository:
    return PlaybackRepository(get_playback_redis_client())


@lru_cache
def get_tracks_play_counter_queue() -> TracksPlayCounterQueue:
    return TracksPlayCounterQueue(async_primary_session)


def get_playback_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    repository: Annotated[PlaybackRepository, Depends(get_playback_repository)],
    play_counter_queue: Annotated[
        TracksPlayCounterQueue, Depends(get_tracks_play_counter_queue)
    ],
) -> PlaybackService:
    return PlaybackService(
        uow=uow,
        repository=repository,
        play_counter_queue=play_counter_queue,
    )
