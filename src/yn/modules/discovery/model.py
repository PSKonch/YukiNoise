from uuid import UUID as PyUUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import UUID as SA_UUID
from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from yn.shared.database import Base


class TrackEmbedding(Base):
    __tablename__ = "track_embedding"
    __table_args__ = (Index("ix_track_embedding_model", "embedding_model"),)

    track_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    document_text: Mapped[str] = mapped_column(nullable=False)
    content_hash: Mapped[str] = mapped_column(nullable=False)
    document_schema_version: Mapped[str] = mapped_column(nullable=False)
    embedding_model: Mapped[str] = mapped_column(nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(nullable=False)
    embedding_vector: Mapped[Vector] = mapped_column(Vector(1536), nullable=False)

    indexed_at: Mapped[str] = mapped_column(nullable=False, server_default=func.now())
