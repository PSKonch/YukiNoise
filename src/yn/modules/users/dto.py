from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from yn.modules.users.model import User


@dataclass
class UserDTO:
    id: UUID
    email: str
    role: str
    is_active: bool
    artist_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    @classmethod
    def from_orm(cls, user: User) -> "UserDTO":
        profile = user.__dict__.get("artist")
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            artist_id=getattr(profile, "id", None),
            created_at=getattr(user, "created_at", None),
            updated_at=getattr(user, "updated_at", None),
            deleted_at=getattr(user, "deleted_at", None),
        )
