from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from minio.error import S3Error  # type: ignore[import-untyped]

from yn.modules.posts.route import router as posts_router
from yn.modules.profiles.route import router as profiles_router
from yn.modules.users.route import router as users_router
from yn.shared.errors import register_exception_handlers
from yn.shared.minio import MinioStorage
from yn.shared.settings import settings

# Global MinIO storage instance
minio_storage: MinioStorage | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    print("Starting up...")
    global minio_storage

    minio_storage = MinioStorage.create(
        {
            "endpoint": settings.minio_endpoint,
            "access_key": settings.minio_access_key,
            "secret_key": settings.minio_secret_key,
            "secure": settings.minio_secure,
        }
    )

    # Create bucket if it doesn't exist
    try:
        await minio_storage._client.stat_bucket(settings.minio_bucket)
        print(f"Bucket '{settings.minio_bucket}' already exists")
    except S3Error as e:
        if e.code == "NoSuchBucket":
            await minio_storage._client.make_bucket(settings.minio_bucket)
            print(f"Bucket '{settings.minio_bucket}' created successfully")
        else:
            raise

    yield

    # Shutdown
    print("Shutting down...")
    if minio_storage:
        await minio_storage.close()


app = FastAPI(
    title="Yukinoise API",
    description="API for Yukinoise, a music higload service built with FastAPI and Python for independent artists",
    version="0.0.1",
    lifespan=lifespan,
)


def get_minio() -> MinioStorage:
    """Get the MinIO storage instance."""
    if minio_storage is None:
        raise RuntimeError("MinIO storage not initialized")
    return minio_storage


register_exception_handlers(app)

app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(posts_router)


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"message": "health check passed"}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        workers=settings.app_workers,
    )
