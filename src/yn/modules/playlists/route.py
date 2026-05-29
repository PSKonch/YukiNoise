from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.playlists.deps import get_playlist_read_service, get_playlist_service
from yn.modules.playlists.errors import EmptyPlaylistUpdateError
from yn.modules.playlists.schemas import (
    PlaylistCreate,
    PlaylistRead,
    PlaylistTrackRead,
    PlaylistUpdate,
)
from yn.modules.playlists.service import PlaylistService
from yn.modules.users.auth import get_current_user
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/playlists", tags=["playlists"])


# Public read
@router.get("/")
async def get_playlists(
    playlist_service: Annotated[PlaylistService, Depends(get_playlist_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[PlaylistRead]:
    playlists = await playlist_service.get_playlists(
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        PlaylistRead.model_validate(playlist, from_attributes=True)
        for playlist in playlists
    ]


@router.get("/{playlist_id:uuid}")
async def get_playlist_by_id(
    playlist_service: Annotated[PlaylistService, Depends(get_playlist_read_service)],
    playlist_id: UUID,
) -> PlaylistRead:
    playlist = await playlist_service.get_playlist_by_id(playlist_id)
    return PlaylistRead.model_validate(playlist, from_attributes=True)


@router.get("/{playlist_id:uuid}/tracks")
async def get_playlist_tracks(
    playlist_service: Annotated[PlaylistService, Depends(get_playlist_read_service)],
    playlist_id: UUID,
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[PlaylistTrackRead]:
    tracks = await playlist_service.get_playlist_tracks(
        playlist_id=playlist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        PlaylistTrackRead.model_validate(track, from_attributes=True)
        for track in tracks
    ]


# Owner read
@router.get("/me")
async def get_owned_playlists(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playlist_service: Annotated[PlaylistService, Depends(get_playlist_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[PlaylistRead]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    playlists = await playlist_service.get_owned_playlists(
        artist_id=current_user.artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        PlaylistRead.model_validate(playlist, from_attributes=True)
        for playlist in playlists
    ]


@router.get("/me/{playlist_id:uuid}")
async def get_owned_playlist_by_id(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playlist_service: Annotated[PlaylistService, Depends(get_playlist_service)],
    playlist_id: UUID,
) -> PlaylistRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    playlist = await playlist_service.get_owned_playlist_by_id(
        playlist_id=playlist_id,
        artist_id=current_user.artist_id,
    )
    return PlaylistRead.model_validate(playlist, from_attributes=True)


@router.get("/me/{playlist_id:uuid}/tracks")
async def get_owned_playlist_tracks(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playlist_service: Annotated[PlaylistService, Depends(get_playlist_service)],
    playlist_id: UUID,
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[PlaylistTrackRead]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    tracks = await playlist_service.get_owned_playlist_tracks(
        playlist_id=playlist_id,
        artist_id=current_user.artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        PlaylistTrackRead.model_validate(track, from_attributes=True)
        for track in tracks
    ]


# Owner write
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


@router.patch("/{playlist_id:uuid}")
async def update_playlist(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playlist_service: Annotated[PlaylistService, Depends(get_playlist_service)],
    playlist_id: UUID,
    payload: PlaylistUpdate,
) -> PlaylistRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    if (
        payload.title is None
        and payload.description is None
        and payload.cover_url is None
        and payload.is_private is None
    ):
        raise EmptyPlaylistUpdateError

    playlist = await playlist_service.update_playlist(
        playlist_id=playlist_id,
        artist_id=current_user.artist_id,
        title=payload.title,
        description=payload.description,
        cover_url=payload.cover_url,
        is_private=payload.is_private,
    )
    return PlaylistRead.model_validate(playlist, from_attributes=True)


@router.delete("/{playlist_id:uuid}")
async def delete_playlist(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playlist_service: Annotated[PlaylistService, Depends(get_playlist_service)],
    playlist_id: UUID,
) -> dict[str, str]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    await playlist_service.delete_playlist(
        playlist_id=playlist_id,
        artist_id=current_user.artist_id,
    )

    return {"detail": "Playlist deleted successfully"}


@router.post("/{playlist_id:uuid}/tracks/{track_id:uuid}")
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


@router.delete("/{playlist_id:uuid}/tracks/{track_id:uuid}")
async def remove_track_from_playlist(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playlist_service: Annotated[PlaylistService, Depends(get_playlist_service)],
    playlist_id: UUID,
    track_id: UUID,
) -> dict[str, str]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    await playlist_service.remove_track_from_playlist(
        playlist_id=playlist_id,
        track_id=track_id,
        artist_id=current_user.artist_id,
    )

    return {"detail": "Track removed from playlist successfully"}
