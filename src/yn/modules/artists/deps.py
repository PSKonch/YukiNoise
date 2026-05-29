from typing import Annotated

from fastapi import Depends

from yn.modules.artists.service import ArtistService
from yn.shared.unit_of_work import UnitOfWork, get_read_uow, get_uow


def get_artist_service(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> ArtistService:
    return ArtistService(uow)


def get_artist_read_service(
    uow: Annotated[UnitOfWork, Depends(get_read_uow)],
) -> ArtistService:
    return ArtistService(uow)
