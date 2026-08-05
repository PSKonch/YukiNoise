from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.artists.schemas import ArtistRead
from yn.modules.auth.auth import get_current_user
from yn.modules.follows.deps import get_follow_read_service, get_follow_service
from yn.modules.follows.schemas import FollowRead, FollowStatus
from yn.modules.follows.service import FollowService
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/follows", tags=["follows"])


@router.get("/{artist_id:uuid}/followers")
async def get_followers(
    artist_id: UUID,
    follow_service: Annotated[FollowService, Depends(get_follow_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ArtistRead]:
    artists = await follow_service.get_followers(
        artist_id=artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ArtistRead.model_validate(artist, from_attributes=True) for artist in artists
    ]


@router.get("/{artist_id:uuid}/following")
async def get_following(
    artist_id: UUID,
    follow_service: Annotated[FollowService, Depends(get_follow_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ArtistRead]:
    artists = await follow_service.get_following(
        artist_id=artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ArtistRead.model_validate(artist, from_attributes=True) for artist in artists
    ]


@router.get("/{artist_id:uuid}/status")
async def get_follow_status(
    artist_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    follow_service: Annotated[FollowService, Depends(get_follow_service)],
) -> FollowStatus:
    follower_id = _require_artist_id(current_user)
    is_following = await follow_service.is_following(
        follower_id=follower_id,
        followed_id=artist_id,
    )
    return FollowStatus(is_following=is_following)


@router.post("/{artist_id:uuid}", status_code=status.HTTP_201_CREATED)
async def follow_artist(
    artist_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    follow_service: Annotated[FollowService, Depends(get_follow_service)],
) -> FollowRead:
    follower_id = _require_artist_id(current_user)
    follow = await follow_service.follow(
        follower_id=follower_id,
        followed_id=artist_id,
    )
    return FollowRead.model_validate(follow, from_attributes=True)


@router.delete("/{artist_id:uuid}")
async def unfollow_artist(
    artist_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    follow_service: Annotated[FollowService, Depends(get_follow_service)],
) -> dict[str, str]:
    follower_id = _require_artist_id(current_user)
    await follow_service.unfollow(
        follower_id=follower_id,
        followed_id=artist_id,
    )
    return {"detail": "Artist unfollowed successfully"}


def _require_artist_id(current_user: UserDTO) -> UUID:
    if current_user.artist_id is None:
        raise ArtistNotFoundError
    return current_user.artist_id
