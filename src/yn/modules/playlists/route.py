from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.playlists.deps import get_playlist_service
from yn.modules.playlists.schemas import PlaylistCreate, PlaylistRead
from yn.modules.playlists.service import PlaylistService
from yn.modules.users.auth import get_current_user
from yn.modules.users.dto import UserDTO

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.post("/")
async def create_playlist(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playlist_service: Annotated[PlaylistService, Depends(get_playlist_service)],
    payload: PlaylistCreate,
) -> PlaylistRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    playlist = await playlist_service.create_playlist(
        artist_id=current_user.artist_id,
        title=payload.title,
        description=payload.description,
        cover_url=payload.cover_url,
        is_private=payload.is_private,
    )
    return PlaylistRead.model_validate(playlist, from_attributes=True)


@router.post("/{playlist_id}/tracks/{track_id}")
async def add_track_to_playlist(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playlist_service: Annotated[PlaylistService, Depends(get_playlist_service)],
    playlist_id: UUID,
    track_id: UUID,
) -> dict[str, str]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    await playlist_service.add_track_to_playlist(
        playlist_id=playlist_id,
        track_id=track_id,
        artist_id=current_user.artist_id,
    )

    return {"detail": "Track added to playlist successfully"}
