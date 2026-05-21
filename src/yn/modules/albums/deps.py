from typing import Annotated

from fastapi import Depends

from yn.modules.albums.service import AlbumService
from yn.shared.minio import MinioStorage, get_minio_storage
from yn.shared.unit_of_work import UnitOfWork, get_uow


def get_album_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    storage: Annotated[MinioStorage, Depends(get_minio_storage)],
) -> AlbumService:
    return AlbumService(uow, storage)
