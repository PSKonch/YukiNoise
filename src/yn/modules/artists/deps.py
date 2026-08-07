from typing import Annotated

from fastapi import Depends

from yn.modules.artists.service import ArtistService
from yn.shared.cache.redis_cache import RedisCache, get_redis_cache
from yn.shared.outbox.publisher import OutboxPublisher, get_outbox_publisher
from yn.shared.singleflight import SingleFlight
from yn.shared.unit_of_work import UnitOfWork, get_read_uow, get_uow

_artist_singleflight = SingleFlight()


def get_artist_singleflight() -> SingleFlight:
    return _artist_singleflight


def get_artist_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    cache: Annotated[RedisCache, Depends(get_redis_cache)],
    singleflight: Annotated[SingleFlight, Depends(get_artist_singleflight)],
    outbox_publisher: Annotated[OutboxPublisher, Depends(get_outbox_publisher)],
) -> ArtistService:
    return ArtistService(uow, cache, singleflight, outbox_publisher)


def get_artist_read_service(
    uow: Annotated[UnitOfWork, Depends(get_read_uow)],
    cache: Annotated[RedisCache, Depends(get_redis_cache)],
    singleflight: Annotated[SingleFlight, Depends(get_artist_singleflight)],
    outbox_publisher: Annotated[OutboxPublisher, Depends(get_outbox_publisher)],
) -> ArtistService:
    return ArtistService(uow, cache, singleflight, outbox_publisher)
