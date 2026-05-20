from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI

from yn.modules.albums.route import router as albums_router
from yn.modules.posts.route import router as posts_router
from yn.modules.profiles.route import router as profiles_router
from yn.modules.tracks.route import router as tracks_router
from yn.modules.users.route import router as users_router
from yn.shared.errors import register_exception_handlers
from yn.shared.minio import MinioStorage, set_minio_storage
from yn.shared.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    print("Starting up...")

    minio_storage = MinioStorage.create(
        {
            "endpoint": settings.minio_endpoint,
            "access_key": settings.minio_access_key,
            "secret_key": settings.minio_secret_key,
            "secure": settings.minio_secure,
        }
    )
    set_minio_storage(minio_storage)

    # Create bucket if it doesn't exist
    if await minio_storage.bucket_exists(settings.minio_bucket):
        print(f"Bucket '{settings.minio_bucket}' already exists")
    else:
        await minio_storage.make_bucket(settings.minio_bucket)
        print(f"Bucket '{settings.minio_bucket}' created successfully")

    yield

    # Shutdown
    print("Shutting down...")
    await minio_storage.close()
    set_minio_storage(None)


app = FastAPI(
    title="Yukinoise API",
    description="API for Yukinoise, a music higload service built with FastAPI and Python for independent artists",
    version="0.0.1",
    lifespan=lifespan,
)


def get_minio() -> MinioStorage:
    """Get the MinIO storage instance."""
    from yn.shared.minio import get_minio_storage

    return get_minio_storage()


register_exception_handlers(app)

app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(posts_router)
app.include_router(albums_router)
app.include_router(tracks_router)


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
