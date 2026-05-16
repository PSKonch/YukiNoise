from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from yn.modules.profiles.model import Profile


@dataclass
class ProfileDTO:
    id: UUID
    user_id: UUID
    displayed_name: str
    bio: str | None = None
    social_links: dict[str, str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_orm(cls, profile: "Profile") -> "ProfileDTO":
        return cls(
            id=profile.id,
            user_id=profile.user_id,
            displayed_name=profile.displayed_name,
            bio=getattr(profile, "bio", None),
            created_at=getattr(profile, "created_at", None),
            updated_at=getattr(profile, "updated_at", None),
        )
