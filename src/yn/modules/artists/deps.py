from typing import Annotated

from fastapi import Depends

from yn.modules.artists.service import ArtistService
from yn.shared.cache.redis_cache import RedisCache, get_redis_cache
from yn.shared.singleflight import SingleFlight
from yn.shared.unit_of_work import UnitOfWork, get_read_uow, get_uow

_artist_singleflight = SingleFlight()


def get_artist_singleflight() -> SingleFlight:
    return _artist_singleflight


def get_artist_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    cache: Annotated[RedisCache, Depends(get_redis_cache)],
    singleflight: Annotated[SingleFlight, Depends(get_artist_singleflight)],
) -> ArtistService:
    return ArtistService(uow, cache, singleflight)


def get_artist_read_service(
    uow: Annotated[UnitOfWork, Depends(get_read_uow)],
    cache: Annotated[RedisCache, Depends(get_redis_cache)],
    singleflight: Annotated[SingleFlight, Depends(get_artist_singleflight)],
) -> ArtistService:
    return ArtistService(uow, cache, singleflight)
