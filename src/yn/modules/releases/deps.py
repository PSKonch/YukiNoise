from typing import Annotated

from fastapi import Depends

from yn.modules.releases.service import ReleaseService
from yn.shared.minio import MinioStorage, get_minio_storage
from yn.shared.unit_of_work import UnitOfWork, get_read_uow, get_uow


def get_release_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    storage: Annotated[MinioStorage, Depends(get_minio_storage)],
) -> ReleaseService:
    return ReleaseService(uow, storage)


def get_release_read_service(
    uow: Annotated[UnitOfWork, Depends(get_read_uow)],
    storage: Annotated[MinioStorage, Depends(get_minio_storage)],
) -> ReleaseService:
    return ReleaseService(uow, storage)
