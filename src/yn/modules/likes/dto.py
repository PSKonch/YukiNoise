from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from yn.modules.likes.enums import TargetType

if TYPE_CHECKING:
    from yn.modules.likes.model import Like


@dataclass(frozen=True, slots=True)
class LikeDTO:
    id: UUID
    artist_id: UUID
    target_type: TargetType
    target_id: UUID
    created_at: datetime

    @classmethod
    def from_orm(cls, like: "Like") -> "LikeDTO":
        return cls(
            id=like.id,
            artist_id=like.artist_id,
            target_type=like.target_type,
            target_id=like.target_id,
            created_at=like.created_at,
        )
