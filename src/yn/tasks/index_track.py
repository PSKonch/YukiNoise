import asyncio
from uuid import UUID

from yn.modules.discovery.deps import get_embedding_provider
from yn.modules.discovery.events import IndexScope
from yn.modules.discovery.indexer import IndexResult, TrackIndexer
from yn.shared.database import async_primary_session
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork
from yn.tasks.broker import broker


@broker.task(retry_on_error=True, max_retries=3)
async def index_track_embedding(track_id: str) -> IndexResult:
    if not settings.discovery_enabled:
        return "skipped"
    provider = await asyncio.to_thread(get_embedding_provider)
    result = await TrackIndexer(async_primary_session, provider).index_track(
        UUID(track_id)
    )
    if result == "stale":
        raise RuntimeError("Track source changed during embedding; retry indexing")
    return result


@broker.task(retry_on_error=True, max_retries=3)
async def index_source_embeddings(source_id: str, scope: IndexScope) -> int:
    """Queue related tracks in bounded pages; retries may queue duplicates."""
    if not settings.discovery_enabled:
        return 0
    if scope not in ("release", "artist"):
        raise ValueError("Index scope must be release or artist")

    identifier = UUID(source_id)
    after: UUID | None = None
    queued = 0
    while True:
        async with async_primary_session() as session:
            async with UnitOfWork(session) as uow:
                track_ids = await uow.track_embeddings.get_track_ids(
                    after=after,
                    limit=100,
                    release_id=identifier if scope == "release" else None,
                    artist_id=identifier if scope == "artist" else None,
                )
        if not track_ids:
            return queued
        for track_id in track_ids:
            await index_track_embedding.kiq(str(track_id))
            queued += 1
        after = track_ids[-1]
