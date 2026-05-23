from yn.modules.releases.service import ReleaseService
from yn.modules.tracks.uploader import TrackUploadPayload, TrackUploadProcessor
from yn.shared.database import async_session
from yn.shared.minio import MinioStorage
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork
from yn.tasks.broker import broker

_worker_storage: MinioStorage | None = None


def _get_worker_storage() -> MinioStorage:
    global _worker_storage
    if _worker_storage is None:
        _worker_storage = MinioStorage.create(
            {
                "endpoint": settings.minio_endpoint,
                "access_key": settings.minio_access_key,
                "secret_key": settings.minio_secret_key,
                "secure": settings.minio_secure,
            }
        )
    return _worker_storage


@broker.task
async def process_track_upload(payload: dict[str, object]) -> None:
    upload_payload = TrackUploadPayload.from_message(payload)
    storage = _get_worker_storage()

    async with async_session() as session:
        async with UnitOfWork(session) as uow:
            processor = TrackUploadProcessor(uow, storage, ReleaseService(uow, storage))
            await processor.process(upload_payload)
