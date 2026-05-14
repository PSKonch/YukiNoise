from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class UserDTO:
    id: UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


def from_orm(user) -> UserDTO:
    return UserDTO(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=getattr(user, "created_at", None),
        updated_at=getattr(user, "updated_at", None),
        deleted_at=getattr(user, "deleted_at", None),
    )
