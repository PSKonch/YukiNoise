from typing import Annotated

from fastapi import Depends

from yn.modules.artists.service import ArtistService
from yn.shared.cache.redis_cache import RedisCache, get_redis_cache
from yn.shared.unit_of_work import UnitOfWork, get_read_uow, get_uow


def get_artist_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    cache: Annotated[RedisCache, Depends(get_redis_cache)],
) -> ArtistService:
    return ArtistService(uow, cache)


def get_artist_read_service(
    uow: Annotated[UnitOfWork, Depends(get_read_uow)],
    cache: Annotated[RedisCache, Depends(get_redis_cache)],
) -> ArtistService:
    return ArtistService(uow, cache)
