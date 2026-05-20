from typing import Annotated

from fastapi import Depends

from yn.modules.tracks.service import TrackService
from yn.shared.minio import MinioStorage, get_minio_storage
from yn.shared.unit_of_work import UnitOfWork, get_uow


def get_track_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    storage: Annotated[MinioStorage, Depends(get_minio_storage)],
) -> TrackService:
    return TrackService(uow, storage)
