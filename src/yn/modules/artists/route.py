from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from yn.modules.artists.deps import get_artist_read_service, get_artist_service
from yn.modules.artists.errors import (
    ArtistNotFoundError,
    EmptyArtistUpdateError,
)
from yn.modules.artists.schemas import ArtistCreate, ArtistRead, ArtistUpdate
from yn.modules.artists.service import ArtistService
from yn.modules.auth.auth import get_current_user
from yn.modules.playlists.schemas import PlaylistRead
from yn.modules.posts.schemas import PostRead
from yn.modules.releases.schemas import ReleaseRead
from yn.modules.tracks.schemas import TrackRead
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/artists", tags=["artists"])


# Public read
@router.get("/")
async def get_all_artists(
    artist_service: Annotated[ArtistService, Depends(get_artist_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ArtistRead]:
    artists = await artist_service.get_all_artists(
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ArtistRead.model_validate(artist, from_attributes=True) for artist in artists
    ]


@router.get("/search")
async def search_artists(
    query: str,
    artist_service: Annotated[ArtistService, Depends(get_artist_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ArtistRead]:
    artists = await artist_service.full_text_search_artists(
        query,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ArtistRead.model_validate(artist, from_attributes=True) for artist in artists
    ]


@router.get("/{artist_id:uuid}")
async def get_artist_by_id(
    artist_id: UUID,
    artist_service: Annotated[ArtistService, Depends(get_artist_read_service)],
) -> ArtistRead:
    artist = await artist_service.get_artist_by_id(artist_id)
    if artist is None:
        raise ArtistNotFoundError
    return ArtistRead.model_validate(artist, from_attributes=True)


@router.get("/{artist_id:uuid}/releases")
async def get_artist_releases(
    artist_id: UUID,
    artist_service: Annotated[ArtistService, Depends(get_artist_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ReleaseRead]:
    artist = await artist_service.get_artist_by_id(artist_id)
    if artist is None:
        raise ArtistNotFoundError

    releases = await artist_service.get_artist_releases(
        artist_id=artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ReleaseRead.model_validate(release, from_attributes=True)
        for release in releases
    ]


@router.get("/{artist_id:uuid}/tracks")
async def get_artist_tracks(
    artist_id: UUID,
    artist_service: Annotated[ArtistService, Depends(get_artist_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[TrackRead]:
    artist = await artist_service.get_artist_by_id(artist_id)
    if artist is None:
        raise ArtistNotFoundError

    tracks = await artist_service.get_artist_tracks(
        artist_id=artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [TrackRead.model_validate(track, from_attributes=True) for track in tracks]


@router.get("/{artist_id:uuid}/posts")
async def get_artist_posts(
    artist_id: UUID,
    artist_service: Annotated[ArtistService, Depends(get_artist_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[PostRead]:
    artist = await artist_service.get_artist_by_id(artist_id)
    if artist is None:
        raise ArtistNotFoundError

    posts = await artist_service.get_artist_posts(
        artist_id=artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [PostRead.model_validate(post, from_attributes=True) for post in posts]


@router.get("/{artist_id:uuid}/playlists")
async def get_artist_playlists(
    artist_id: UUID,
    artist_service: Annotated[ArtistService, Depends(get_artist_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[PlaylistRead]:
    artist = await artist_service.get_artist_by_id(artist_id)
    if artist is None:
        raise ArtistNotFoundError

    playlists = await artist_service.get_artist_playlists(
        artist_id=artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        PlaylistRead.model_validate(playlist, from_attributes=True)
        for playlist in playlists
    ]


# Owner read/write
@router.get("/me")
async def read_current_user_artist_profile(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    artist_service: Annotated[ArtistService, Depends(get_artist_service)],
) -> ArtistRead:
    artist = await artist_service.get_artist_by_user_id(current_user.id)
    if artist is None:
        raise ArtistNotFoundError
    return ArtistRead.model_validate(artist, from_attributes=True)


@router.get("/me/releases")
async def get_owned_releases(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    artist_service: Annotated[ArtistService, Depends(get_artist_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ReleaseRead]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    releases = await artist_service.get_owned_releases(
        artist_id=current_user.artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ReleaseRead.model_validate(release, from_attributes=True)
        for release in releases
    ]


@router.get("/me/tracks")
async def get_owned_tracks(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    artist_service: Annotated[ArtistService, Depends(get_artist_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[TrackRead]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    tracks = await artist_service.get_owned_tracks(
        artist_id=current_user.artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [TrackRead.model_validate(track, from_attributes=True) for track in tracks]


@router.get("/me/posts")
async def get_owned_posts(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    artist_service: Annotated[ArtistService, Depends(get_artist_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[PostRead]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    posts = await artist_service.get_owned_posts(
        artist_id=current_user.artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [PostRead.model_validate(post, from_attributes=True) for post in posts]


@router.get("/me/playlists")
async def get_owned_playlists(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    artist_service: Annotated[ArtistService, Depends(get_artist_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[PlaylistRead]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    playlists = await artist_service.get_owned_playlists(
        artist_id=current_user.artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        PlaylistRead.model_validate(playlist, from_attributes=True)
        for playlist in playlists
    ]


@router.post("/")
async def create_artist(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    artist_service: Annotated[ArtistService, Depends(get_artist_service)],
    payload: ArtistCreate,
) -> dict[str, str]:
    await artist_service.create_artist(
        user_id=current_user.id,
        displayed_name=payload.displayed_name,
        bio=payload.bio,
        social_links=payload.social_links,
    )
    return {"detail": "Artist created successfully"}


@router.put("/me")
async def update_current_user_artist_profile(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    artist_service: Annotated[ArtistService, Depends(get_artist_service)],
    payload: ArtistUpdate,
) -> dict[str, str]:
    if (
        payload.displayed_name is None
        and payload.bio is None
        and payload.social_links is None
    ):
        raise EmptyArtistUpdateError

    artist_exists = await artist_service.update_artist(
        user_id=current_user.id,
        displayed_name=payload.displayed_name,
        bio=payload.bio,
        social_links=payload.social_links,
    )

    if not artist_exists:
        raise ArtistNotFoundError

    return {"detail": "Artist updated successfully"}


@router.delete("/me")
async def delete_current_user_artist_profile(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    artist_service: Annotated[ArtistService, Depends(get_artist_service)],
) -> dict[str, str]:
    artist_exists = await artist_service.hard_delete_artist(user_id=current_user.id)

    if not artist_exists:
        raise ArtistNotFoundError

    return {"detail": "Artist deleted successfully"}
