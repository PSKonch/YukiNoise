from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from yn.modules.artists.deps import get_artist_service
from yn.modules.artists.errors import (
    ArtistNotFoundError,
    EmptyArtistUpdateError,
)
from yn.modules.artists.schemas import ArtistCreate, ArtistRead, ArtistUpdate
from yn.modules.artists.service import ArtistService
from yn.modules.users.auth import get_current_user
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/artists", tags=["artists"])


# Public read
@router.get("/")
async def get_all_artists(
    artist_service: Annotated[ArtistService, Depends(get_artist_service)],
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
    artist_service: Annotated[ArtistService, Depends(get_artist_service)],
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


@router.get("/{artist_id}")
async def get_artist_by_id(
    artist_id: UUID,
    artist_service: Annotated[ArtistService, Depends(get_artist_service)],
) -> ArtistRead:
    artist = await artist_service.get_artist_by_id(artist_id)
    if artist is None:
        raise ArtistNotFoundError
    return ArtistRead.model_validate(artist, from_attributes=True)


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
