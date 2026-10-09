from datetime import datetime
from uuid import UUID as PyUUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import UUID as SA_UUID
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from yn.shared.database import Base


class TrackEmbedding(Base):
    __tablename__ = "track_embedding"
    __table_args__ = (
        Index("ix_track_embedding_model", "embedding_model"),
        CheckConstraint(
            "embedding_dimension = 768", name="ck_track_embedding_dimension"
        ),
    )

    track_id: Mapped[PyUUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    document_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(nullable=False)
    document_schema_version: Mapped[int] = mapped_column(nullable=False)
    embedding_model: Mapped[str] = mapped_column(nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(nullable=False)
    embedding_vector: Mapped[list[float]] = mapped_column(Vector(768), nullable=False)

    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
