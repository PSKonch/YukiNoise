from dataclasses import dataclass
from typing import Any, AsyncIterator, BinaryIO

from minio.api import Minio  # type: ignore[import-untyped]
from minio.commonconfig import CopySource  # type: ignore[import-untyped]
from minio.deleteobjects import DeleteObject  # type: ignore[import-untyped]
from minio.error import S3Error  # type: ignore[import-untyped]


@dataclass
class StorageObject:
    key: str
    size: int


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
        await self._client.close()

    async def put(
        self,
        bucket: str,
        key: str,
        stream: BinaryIO,
        part_size: int = 5 * 1024 * 1024,
    ) -> int | None:
        await self._client.put_object(
            bucket_name=bucket,
            object_name=key,
            data=stream,
            length=-1,
            part_size=part_size,
        )
        stat_result = await self._client.stat_object(bucket, key)
        return int(stat_result.size)

    async def move(
        self,
        bucket: str,
        source_key: str,
        destination_key: str,
    ) -> None:
        await self._client.copy_object(
            bucket_name=bucket,
            object_name=destination_key,
            source=CopySource(bucket, source_key),
        )
        await self.delete(bucket=bucket, key=source_key)

    async def get(self, bucket: str, key: str) -> bytes:
        file = await self._client.get_object(bucket, key)
        return await file.read()  # type: ignore[no-any-return]

    async def delete(self, bucket: str, key: str) -> None:
        await self._client.remove_object(bucket, key)

    async def delete_batch(self, bucket: str, keys: list[str]) -> None:
        delete_objs = [DeleteObject(key) for key in keys]
        await self._client.remove_objects(bucket, delete_objs)

    async def is_file(self, bucket: str, key: str) -> bool:
        await self._client.stat_object(bucket, key)
        return True

    async def list_files(
        self, bucket: str, prefix: str = "", recursive: bool = False
    ) -> AsyncIterator[StorageObject]:
        try:
            objects = await self._client.list_objects(
                bucket, prefix=prefix, recursive=recursive
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
