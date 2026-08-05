from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis

from yn.modules.artists.route import router as artists_router
from yn.modules.auth.route import router as auth_router
from yn.modules.playback.deps import (
    get_playback_redis_client,
    get_tracks_play_counter_queue,
)
from yn.modules.playback.route import router as playback_router
from yn.modules.playlists.kafka import router as playlists_kafka_router
from yn.modules.playlists.route import router as playlists_router
from yn.modules.posts.route import router as posts_router
from yn.modules.releases.route import router as releases_router
from yn.modules.tracks.route import router as tracks_router
from yn.modules.users.route import router as users_router
from yn.shared.cache.redis_cache import RedisCache, set_redis_cache
from yn.shared.database import get_replica_status
from yn.shared.errors import register_exception_handlers
from yn.shared.minio import MinioStorage, set_minio_storage
from yn.shared.publisher import kafka_broker
from yn.shared.redis_manager import RedisManager
from yn.shared.settings import settings
from yn.tasks.broker import broker

kafka_broker.include_router(playlists_kafka_router)


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

    await kafka_broker.start()

    # Create bucket if it doesn't exist
    if await minio_storage.bucket_exists(settings.minio_bucket):
        print(f"Bucket '{settings.minio_bucket}' already exists")
    else:
        await minio_storage.make_bucket(settings.minio_bucket)
        print(f"Bucket '{settings.minio_bucket}' created successfully")

    await broker.startup()
    play_counter_queue = get_tracks_play_counter_queue()
    play_counter_queue.start()

    yield

    # Shutdown
    print("Shutting down...")
    await play_counter_queue.stop()
    await broker.shutdown()
    await kafka_broker.stop()
    await redis_manager.close()
    await get_playback_redis_client().aclose()
    set_redis_cache(None)
    await minio_storage.close()
    set_minio_storage(None)


app = FastAPI(
    title="Yukinoise API",
    description="API for Yukinoise, a music higload service built with FastAPI and Python for independent artists",
    version="0.0.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Report whether the HTTP process is running."""
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness_check() -> JSONResponse:
    """Fail readiness when the read replica is unavailable, stale, or promoted."""
    try:
        replica_status = await get_replica_status()
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "replica": "unreachable"},
        )

    is_healthy = (
        replica_status.is_replica
        and replica_status.lag_bytes is not None
        and replica_status.lag_bytes <= settings.replica_lag_threshold_bytes
    )
    response_status = (
        status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(
        status_code=response_status,
        content={
            "status": "ok" if is_healthy else "unavailable",
            "replica": {
                "is_replica": replica_status.is_replica,
                "lag_bytes": replica_status.lag_bytes,
                "lag_threshold_bytes": settings.replica_lag_threshold_bytes,
            },
        },
    )


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
