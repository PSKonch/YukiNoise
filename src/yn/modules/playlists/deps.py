from typing import Annotated

from fastapi import Depends

from yn.modules.playlists.service import PlaylistService
from yn.shared.unit_of_work import UnitOfWork, get_read_uow, get_uow


def get_playlist_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> PlaylistService:
    return PlaylistService(uow)


def get_playlist_read_service(
    uow: Annotated[UnitOfWork, Depends(get_read_uow)],
) -> PlaylistService:
    return PlaylistService(uow)
