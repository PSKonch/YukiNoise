from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
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
