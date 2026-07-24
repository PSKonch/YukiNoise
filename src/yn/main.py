from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis

from yn.modules.artists.route import router as artists_router
from yn.modules.auth.route import router as auth_router
from yn.modules.playback.route import router as playback_router
from yn.modules.playlists.route import router as playlists_router
from yn.modules.posts.route import router as posts_router
from yn.modules.releases.route import router as releases_router
from yn.modules.tracks.route import router as tracks_router
from yn.modules.users.route import router as users_router
from yn.shared.cache.redis_cache import RedisCache, set_redis_cache
from yn.shared.errors import register_exception_handlers
from yn.shared.minio import MinioStorage, set_minio_storage
from yn.shared.redis_manager import RedisManager
from yn.shared.settings import settings
from yn.tasks.broker import broker


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

    redis_manager = RedisManager(
        Redis.from_url(settings.redis_url, decode_responses=True)
    )
    set_redis_cache(RedisCache(redis_manager))

    # Create bucket if it doesn't exist
    if await minio_storage.bucket_exists(settings.minio_bucket):
        print(f"Bucket '{settings.minio_bucket}' already exists")
    else:
        await minio_storage.make_bucket(settings.minio_bucket)
        print(f"Bucket '{settings.minio_bucket}' created successfully")

    await broker.startup()

    yield

    # Shutdown
    print("Shutting down...")
    await broker.shutdown()
    await redis_manager.close()
    set_redis_cache(None)
    await minio_storage.close()
    set_minio_storage(None)


app = FastAPI(
    title="Yukinoise API",
    description="API for Yukinoise, a music higload service built with FastAPI and Python for independent artists",
    version="0.0.1",
    lifespan=lifespan,
)


Instrumentator().instrument(app).expose(app)


def get_minio() -> MinioStorage:
    """Get the MinIO storage instance."""
    from yn.shared.minio import get_minio_storage

    return get_minio_storage()


register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(artists_router)
app.include_router(playback_router)
app.include_router(playlists_router)
app.include_router(posts_router)
app.include_router(releases_router)
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
