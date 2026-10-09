from contextlib import AbstractAsyncContextManager
from typing import Callable, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.discovery.document_builder import DocumentBuilder
from yn.modules.discovery.embedding_provider import EmbeddingProvider, validate_vector
from yn.modules.discovery.errors import DiscoveryInvalidModelOutputError
from yn.shared.unit_of_work import UnitOfWork

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]
IndexResult = Literal["indexed", "skipped", "deleted", "stale", "pending"]


class TrackIndexer:
    def __init__(
        self, session_factory: SessionFactory, provider: EmbeddingProvider
    ) -> None:
        self._session_factory = session_factory
        self._provider = provider

    async def index_track(
        self, track_id: UUID, *, dry_run: bool = False
    ) -> IndexResult:
        async with self._session_factory() as session:
            async with UnitOfWork(session) as uow:
                source = await uow.track_embeddings.get_source(track_id)
                if source is not None:
                    document = DocumentBuilder(source).build()
                    if await uow.track_embeddings.is_current(
                        track_id,
                        document,
                        model_name=self._provider.model_name,
                        dimensions=self._provider.model_dimensions,
                    ):
                        return "skipped"

        if dry_run:
            return "pending"

        if source is None:
            async with self._session_factory() as session:
                async with UnitOfWork(session) as uow:
                    if (
                        await uow.track_embeddings.get_source(
                            track_id, is_for_update=True
                        )
                    ) is not None:
                        return "stale"

                    await uow.track_embeddings.delete(track_id)
                    await uow.commit()
            return "deleted"

        vectors = await self._provider.embed_documents([document.text])
        if len(vectors) != 1:
            raise DiscoveryInvalidModelOutputError
        vector = validate_vector(vectors[0], self._provider.model_dimensions)

        async with self._session_factory() as session:
            async with UnitOfWork(session) as uow:
                latest_source = await uow.track_embeddings.get_source(
                    track_id, is_for_update=True
                )
                if latest_source is None:
                    await uow.track_embeddings.delete(track_id)
                    await uow.commit()
                    return "deleted"
                if (
                    DocumentBuilder(latest_source).build().content_hash
                    != document.content_hash
                ):
                    return "stale"
                if await uow.track_embeddings.is_current(
                    track_id,
                    document,
                    model_name=self._provider.model_name,
                    dimensions=self._provider.model_dimensions,
                ):
                    return "skipped"
                await uow.track_embeddings.upsert(
                    track_id,
                    document,
                    vector,
                    model_name=self._provider.model_name,
                    dimensions=self._provider.model_dimensions,
                )
                await uow.commit()
        return "indexed"
