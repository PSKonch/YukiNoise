from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CommentaryContent(BaseModel):
    content: str = Field(min_length=1, max_length=5000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Commentary content must not be blank")
        return normalized


class CommentaryCreate(CommentaryContent):
    commentary_id: UUID | None = None


class CommentaryUpdate(CommentaryContent):
    pass


class CommentaryRead(CommentaryContent):
    id: UUID
    artist_id: UUID
    post_id: UUID
    commentary_id: UUID | None = None
    author_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
