from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from yn.modules.posts.model import Post


@dataclass
class PostDTO:
    id: UUID
    profile_id: UUID
    title: str
    content: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    @classmethod
    def from_orm(cls, post: "Post") -> "PostDTO":
        return cls(
            id=post.id,
            profile_id=post.profile_id,
            title=post.title,
            content=post.content,
            created_at=getattr(post, "created_at", None),
            updated_at=getattr(post, "updated_at", None),
            deleted_at=getattr(post, "deleted_at", None),
        )
