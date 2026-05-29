from typing import Annotated

from fastapi import Depends

from yn.modules.releases.deps import get_release_read_service, get_release_service
from yn.modules.releases.service import ReleaseService
from yn.modules.tracks.service import TrackService
from yn.shared.unit_of_work import UnitOfWork, get_read_uow, get_uow


def get_track_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    release_service: Annotated[ReleaseService, Depends(get_release_service)],
) -> TrackService:
    return TrackService(uow, release_service)


def get_track_read_service(
    uow: Annotated[UnitOfWork, Depends(get_read_uow)],
    release_service: Annotated[ReleaseService, Depends(get_release_read_service)],
) -> TrackService:
    return TrackService(uow, release_service)
