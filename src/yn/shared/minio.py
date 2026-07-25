import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, AsyncIterator, BinaryIO

from minio import Minio
from minio.commonconfig import CopySource
from minio.deleteobjects import DeleteObject
from minio.error import S3Error


@dataclass
class StorageObject:
    key: str
    size: int


_minio_storage: "MinioStorage | None" = None


class MinioStorage:
    def __init__(
        self, endpoint: str, access_key: str, secret_key: str, secure: bool = True
    ) -> None:
        self._client = Minio(
            endpoint, access_key=access_key, secret_key=secret_key, secure=secure
        )

    @classmethod
    def create(cls, settings: dict[str, Any]) -> "MinioStorage":
        return cls(**settings)

    async def close(self) -> None:
        close = getattr(self._client, "close", None)
        if close is not None:
            await asyncio.to_thread(close)

    async def bucket_exists(self, bucket: str) -> bool:
        return await asyncio.to_thread(self._client.bucket_exists, bucket)

    async def make_bucket(self, bucket: str) -> None:
        await asyncio.to_thread(self._client.make_bucket, bucket)

    async def put(
        self,
        bucket: str,
        key: str,
        stream: BinaryIO,
        part_size: int = 5 * 1024 * 1024,
    ) -> int | None:
        await asyncio.to_thread(
            self._client.put_object,
            bucket_name=bucket,
            object_name=key,
            data=stream,
            length=-1,
            part_size=part_size,
        )
        stat_result = await asyncio.to_thread(self._client.stat_object, bucket, key)
        return stat_result.size or 0

    async def move(
        self,
        bucket: str,
        source_key: str,
        destination_key: str,
    ) -> None:
        await asyncio.to_thread(
            self._client.copy_object,
            bucket_name=bucket,
            object_name=destination_key,
            source=CopySource(bucket, source_key),
        )
        await self.delete(bucket=bucket, key=source_key)

    async def get(self, bucket: str, key: str) -> bytes:
        def read_object() -> bytes:
            file = self._client.get_object(bucket, key)
            try:
                return file.read()
            finally:
                file.close()
                release_conn = getattr(file, "release_conn", None)
                if release_conn is not None:
                    release_conn()

        return await asyncio.to_thread(read_object)

    async def iter_object(
        self, bucket: str, key: str, chunk_size: int = 64 * 1024
    ) -> AsyncIterator[bytes]:
        file = await asyncio.to_thread(self._client.get_object, bucket, key)

        async def close_file() -> None:
            await asyncio.to_thread(file.close)
            release_conn = getattr(file, "release_conn", None)
            if release_conn is not None:
                await asyncio.to_thread(release_conn)

        try:
            while True:
                chunk = await asyncio.to_thread(file.read, chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            await close_file()

    async def stat(self, bucket: str, key: str) -> StorageObject:
        result = await asyncio.to_thread(self._client.stat_object, bucket, key)
        return StorageObject(key=key, size=int(result.size or 0))

    async def iter_object_range(
        self,
        bucket: str,
        key: str,
        *,
        offset: int,
        length: int,
        chunk_size: int = 64 * 1024,
    ) -> AsyncIterator[bytes]:
        file = await asyncio.to_thread(
            self._client.get_object,
            bucket,
            key,
            offset=offset,
            length=length,
        )
        remaining = length
        try:
            while remaining > 0:
                chunk = await asyncio.to_thread(file.read, min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
        finally:
            await asyncio.to_thread(file.close)
            release_conn = getattr(file, "release_conn", None)
            if release_conn is not None:
                await asyncio.to_thread(release_conn)

    async def presigned_get_object(
        self, bucket: str, key: str, expires_seconds: int = 3600
    ) -> str:
        return await asyncio.to_thread(
            self._client.presigned_get_object,
            bucket,
            key,
            expires=timedelta(seconds=expires_seconds),
        )

    async def delete(self, bucket: str, key: str) -> None:
        await asyncio.to_thread(self._client.remove_object, bucket, key)

    async def delete_batch(self, bucket: str, keys: list[str]) -> None:
        delete_objs = [DeleteObject(key) for key in keys]
        await asyncio.to_thread(self._client.remove_objects, bucket, delete_objs)

    async def is_file(self, bucket: str, key: str) -> bool:
        await asyncio.to_thread(self._client.stat_object, bucket, key)
        return True

    async def list_files(
        self, bucket: str, prefix: str = "", recursive: bool = False
    ) -> AsyncIterator[StorageObject]:
        try:
            objects = await asyncio.to_thread(
                lambda: list(
                    self._client.list_objects(
                        bucket, prefix=prefix, recursive=recursive
                    )
                )
            )
            for obj in objects:
                yield StorageObject(
                    key=obj.object_name,
                    size=obj.size,
                )
        except Exception as e:
            if isinstance(e, S3Error) and e.code == "NoSuchBucket":
                return
            raise


def set_minio_storage(storage: "MinioStorage | None") -> None:
    global _minio_storage
    _minio_storage = storage


def get_minio_storage() -> "MinioStorage":
    if _minio_storage is None:
        raise RuntimeError("MinIO storage not initialized")
    return _minio_storage
