from typing import Annotated

from fastapi import Depends

from yn.modules.albums.deps import get_album_service
from yn.modules.albums.service import AlbumService
from yn.modules.tracks.service import TrackService
from yn.shared.unit_of_work import UnitOfWork, get_uow


def get_track_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    album_service: Annotated[AlbumService, Depends(get_album_service)],
) -> TrackService:
    return TrackService(uow, album_service)
