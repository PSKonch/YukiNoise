from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from yn.modules.follows.model import Follow


@dataclass(frozen=True, slots=True)
class FollowDTO:
    id: UUID
    follower_id: UUID
    followed_id: UUID
    created_at: datetime

    @classmethod
    def from_orm(cls, follow: "Follow") -> "FollowDTO":
        return cls(
            id=follow.id,
            follower_id=follow.follower_id,
            followed_id=follow.followed_id,
            created_at=follow.created_at,
        )
