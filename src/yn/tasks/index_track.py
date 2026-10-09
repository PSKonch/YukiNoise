import asyncio
from uuid import UUID

from yn.modules.discovery.deps import get_embedding_provider
from yn.modules.discovery.indexer import IndexResult, TrackIndexer
from yn.shared.database import async_primary_session
from yn.shared.settings import settings
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
