from typing import Sequence
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.artists.model import Artist
from yn.modules.discovery.document_builder import (
    TrackEmbeddingDocument,
    TrackIndexSource,
)
from yn.modules.discovery.dto import TrackCandidateDTO
from yn.modules.discovery.model import TrackEmbedding
from yn.modules.releases.model import Release
from yn.modules.tracks.model import Track


class TrackEmbeddingRepository:
    model = TrackEmbedding

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _create_source(
        track: Track, artist: Artist, release: Release
    ) -> TrackIndexSource:
        return TrackIndexSource(
            track_id=str(track.id),
            track_title=track.title,
            genres=tuple(track.genres),
            artist_name=artist.displayed_name,
            artist_bio=artist.bio,
            release_title=release.title,
            release_description=release.description,
            featured_artist_names=tuple(
                featured_artist.displayed_name
                for featured_artist in track.featured_artists
                if featured_artist.deleted_at is None
            ),
        )

    async def get_source(
        self, track_id: UUID, is_for_update: bool = False
    ) -> TrackIndexSource | None:
        query = (
            select(Track, Artist, Release)
            .join(Release, Release.id == Track.release_id)
            .join(Artist, Artist.id == Release.artist_id)
            .where(
                Track.id == track_id,
                Track.deleted_at.is_(None),
                Release.publicly_visible_clause(),
                Artist.deleted_at.is_(None),
            )
        )
        if is_for_update:
            query = query.with_for_update(of=[Track, Artist, Release])
        result = await self._session.execute(query)
        row = result.one_or_none()
        return self._create_source(*row) if row else None

    async def is_current(
        self,
        track_id: UUID,
        document: TrackEmbeddingDocument,
        *,
        model_name: str,
        dimensions: int,
    ) -> bool:
        query = select(self.model.track_id).where(
            self.model.track_id == track_id,
            self.model.content_hash == document.content_hash,
            self.model.document_schema_version == document.schema_version,
            self.model.embedding_model == model_name,
            self.model.embedding_dimension == dimensions,
        )
        return (await self._session.execute(query)).scalar_one_or_none() is not None

    async def upsert(
        self,
        track_id: UUID,
        document: TrackEmbeddingDocument,
        embedding_vector: list[float],
        *,
        model_name: str,
        dimensions: int,
    ) -> None:
        stmt = insert(self.model).values(
            track_id=track_id,
            document_text=document.text,
            content_hash=document.content_hash,
            document_schema_version=document.schema_version,
            embedding_model=model_name,
            embedding_dimension=dimensions,
            embedding_vector=embedding_vector,
            indexed_at=func.now(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[self.model.track_id],
            set_={
                "document_text": stmt.excluded.document_text,
                "content_hash": stmt.excluded.content_hash,
                "document_schema_version": stmt.excluded.document_schema_version,
                "embedding_model": stmt.excluded.embedding_model,
                "embedding_dimension": stmt.excluded.embedding_dimension,
                "embedding_vector": stmt.excluded.embedding_vector,
                "indexed_at": func.now(),
            },
        )
        await self._session.execute(stmt)

    async def delete(self, track_id: UUID) -> None:
        stmt = delete(self.model).where(self.model.track_id == track_id)
        await self._session.execute(stmt)

    async def get_track_ids(
        self,
        *,
        after: UUID | None = None,
        limit: int = 100,
        release_id: UUID | None = None,
        artist_id: UUID | None = None,
    ) -> list[UUID]:
        query = select(Track.id).order_by(Track.id).limit(limit)
        if release_id is not None:
            query = query.where(Track.release_id == release_id)
        if artist_id is not None:
            query = query.join(Release, Release.id == Track.release_id).where(
                or_(
                    Release.artist_id == artist_id,
                    Track.featured_artists.any(Artist.id == artist_id),
                )
            )
        if after is not None:
            query = query.where(Track.id > after)
        return list((await self._session.execute(query)).scalars().all())

    async def search(
        self,
        query_vector: list[float],
        *,
        model_name: str,
        dimensions: int,
        schema_version: int,
        limit: int = 20,
    ) -> list[TrackCandidateDTO]:
        distance = self.model.embedding_vector.cosine_distance(query_vector)
        query = (
            (
                (
                    select(
                        Track,
                        Artist,
                        Release,
                        self.model.document_text,
                        self.model.content_hash,
                        distance.label("distance"),
                    )
                )
                .select_from(self.model)
                .join(Track, self.model.track_id == Track.id)
                .join(Release, Release.id == Track.release_id)
                .join(Artist, Artist.id == Release.artist_id)
            )
            .where(
                self.model.embedding_model == model_name,
                self.model.embedding_dimension == dimensions,
                self.model.document_schema_version == schema_version,
                Track.deleted_at.is_(None),
                Artist.deleted_at.is_(None),
                Release.publicly_visible_clause(),
            )
            .order_by(distance, self.model.track_id)
            .limit(limit=limit)
        )
        result = await self._session.execute(query)
        return [
            TrackCandidateDTO(
                track_id=row[0].id,
                source=self._create_source(row[0], row[1], row[2]),
                document_text=row[3],
                content_hash=row[4],
                distance=row[5],
            )
            for row in result.all()
        ]

    async def get_sources(
        self, track_ids: Sequence[UUID]
    ) -> dict[UUID, TrackIndexSource]:
        if not track_ids:
            return {}
        query = (
            select(Track, Artist, Release)
            .join(Release, Release.id == Track.release_id)
            .join(Artist, Artist.id == Release.artist_id)
            .where(
                Track.id.in_(track_ids),
                Track.deleted_at.is_(None),
                Release.publicly_visible_clause(),
                Artist.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(query)
        return {
            row[0].id: self._create_source(row[0], row[1], row[2])
            for row in result.all()
        }
