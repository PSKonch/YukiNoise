from typing import Annotated

from fastapi import Depends

from yn.modules.playlists.service import PlaylistService
from yn.shared.unit_of_work import UnitOfWork, get_uow


def get_playlist_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> PlaylistService:
    return PlaylistService(uow)
