from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from yn.modules.commentaries.model import Commentary


@dataclass
class CommentaryDTO:
    id: UUID
    artist_id: UUID
    post_id: UUID
    commentary_id: UUID | None
    content: str
    author_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    @classmethod
    def from_orm(cls, commentary: "Commentary") -> "CommentaryDTO":
        artist = commentary.__dict__.get("artist")
        return cls(
            id=commentary.id,
            artist_id=commentary.artist_id,
            post_id=commentary.post_id,
            commentary_id=commentary.commentary_id,
            content=commentary.content,
            author_name=getattr(artist, "displayed_name", None),
            created_at=getattr(commentary, "created_at", None),
            updated_at=getattr(commentary, "updated_at", None),
            deleted_at=getattr(commentary, "deleted_at", None),
        )
