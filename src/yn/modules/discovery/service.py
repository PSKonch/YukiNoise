from typing import Sequence

from sqlalchemy.exc import SQLAlchemyError

from yn.modules.discovery.document_builder import DocumentBuilder
from yn.modules.discovery.dto import SearchTrackDTO, TrackCandidateDTO
from yn.modules.discovery.embedding_provider import EmbeddingProvider, validate_vector
from yn.modules.discovery.errors import DiscoveryIndexUnavailableError
from yn.modules.discovery.generation_provider import CurationGenerator
from yn.modules.discovery.indexer import SessionFactory
from yn.modules.discovery.schemas import GeneratedCuration
from yn.modules.discovery.validation import validate_curation
from yn.shared.unit_of_work import UnitOfWork


class DiscoveryService:
    def __init__(
        self,
        session_factory: SessionFactory,
        provider: EmbeddingProvider,
        generator: CurationGenerator | None = None,
        *,
        retrieval_limit: int = 20,
    ) -> None:
        self._session_factory = session_factory
        self._provider = provider
        self._generator = generator
        self._retrieval_limit = retrieval_limit

    async def retrieve_candidates(
        self, query: str, *, limit: int
    ) -> list[TrackCandidateDTO]:
        query = " ".join(query.split())
        vector = validate_vector(
            await self._provider.embed_query(query), self._provider.model_dimensions
        )

        try:
            async with self._session_factory() as session:
                async with UnitOfWork(session) as uow:
                    candidates = await uow.track_embeddings.search(
                        query_vector=vector,
                        model_name=self._provider.model_name,
                        dimensions=self._provider.model_dimensions,
                        schema_version=DocumentBuilder.SCHEMA_VERSION,
                        limit=limit,
                    )
        except SQLAlchemyError as e:
            raise DiscoveryIndexUnavailableError from e
        return [
            candidate
            for candidate in candidates
            if DocumentBuilder(candidate.source).build().content_hash
            == candidate.content_hash
        ]

    async def search(self, query: str, *, limit: int = 20) -> list[SearchTrackDTO]:
        candidates = await self.retrieve_candidates(query, limit=limit)
        return [SearchTrackDTO.from_candidate(c) for c in candidates]

    async def generate_curation(
        self,
        query: str,
        candidates: Sequence[TrackCandidateDTO],
        *,
        limit: int,
    ) -> GeneratedCuration:
        if self._generator is None:
            raise RuntimeError("Curation generator was not configured")
        return await self._generator.generate(
            query=query, candidates=candidates, limit=limit
        )

    async def hydrate_curation(
        self,
        result: GeneratedCuration,
        candidates: Sequence[TrackCandidateDTO],
    ) -> GeneratedCuration:
        if not result.tracks:
            return GeneratedCuration.empty()
        try:
            async with self._session_factory() as session:
                async with UnitOfWork(session) as uow:
                    current_sources = await uow.track_embeddings.get_sources(
                        [track.track_id for track in result.tracks]
                    )
        except SQLAlchemyError as exc:
            raise DiscoveryIndexUnavailableError from exc
        original = {candidate.track_id: candidate for candidate in candidates}
        tracks = [
            track
            for track in result.tracks
            if track.track_id in current_sources
            and track.track_id in original
            and DocumentBuilder(current_sources[track.track_id]).build().content_hash
            == original[track.track_id].content_hash
        ]
        return (
            result.model_copy(update={"tracks": tracks})
            if tracks
            else GeneratedCuration.empty()
        )

    async def preview(self, query: str, *, limit: int) -> GeneratedCuration:
        candidates = await self.retrieve_candidates(query, limit=self._retrieval_limit)
        if not candidates:
            return GeneratedCuration.empty()
        result = await self.generate_curation(query, candidates, limit=limit)
        result = validate_curation(result, candidates, limit=limit)
        return await self.hydrate_curation(result, candidates)
