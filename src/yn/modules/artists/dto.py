from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from yn.modules.artists.model import Artist


@dataclass
class ArtistDTO:
    id: UUID
    user_id: UUID
    displayed_name: str
    bio: str | None = None
    social_links: dict[str, str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_orm(cls, artist: "Artist") -> "ArtistDTO":
        return cls(
            id=artist.id,
            user_id=artist.user_id,
            displayed_name=artist.displayed_name,
            bio=getattr(artist, "bio", None),
            social_links=getattr(artist, "social_links", None),
            created_at=getattr(artist, "created_at", None),
            updated_at=getattr(artist, "updated_at", None),
        )

    def to_cache(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "displayed_name": self.displayed_name,
            "bio": self.bio,
            "social_links": self.social_links,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_cache(cls, value: dict[str, Any]) -> "ArtistDTO":
        created_at = value["created_at"]
        updated_at = value["updated_at"]
        return cls(
            id=UUID(value["id"]),
            user_id=UUID(value["user_id"]),
            displayed_name=value["displayed_name"],
            bio=value["bio"],
            social_links=value["social_links"],
            created_at=datetime.fromisoformat(created_at) if created_at else None,
            updated_at=datetime.fromisoformat(updated_at) if updated_at else None,
        )
