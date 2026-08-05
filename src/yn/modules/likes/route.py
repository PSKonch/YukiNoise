from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.auth.auth import get_current_user
from yn.modules.likes.deps import get_like_service
from yn.modules.likes.enums import TargetType
from yn.modules.likes.schemas import LikeRead, LikeStatus
from yn.modules.likes.service import LikeService
from yn.modules.users.dto import UserDTO

router = APIRouter(prefix="/likes", tags=["likes"])


@router.get("/{target_type}/{target_id:uuid}/status")
async def get_like_status(
    target_type: TargetType,
    target_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    like_service: Annotated[LikeService, Depends(get_like_service)],
) -> LikeStatus:
    artist_id = _require_artist_id(current_user)
    is_liked = await like_service.is_liked(
        artist_id=artist_id,
        target_type=target_type,
        target_id=target_id,
    )
    return LikeStatus(is_liked=is_liked)


@router.post(
    "/{target_type}/{target_id:uuid}",
    status_code=status.HTTP_201_CREATED,
)
async def like_target(
    target_type: TargetType,
    target_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    like_service: Annotated[LikeService, Depends(get_like_service)],
) -> LikeRead:
    artist_id = _require_artist_id(current_user)
    like = await like_service.like(
        artist_id=artist_id,
        target_type=target_type,
        target_id=target_id,
    )
    return LikeRead.model_validate(like, from_attributes=True)


@router.delete("/{target_type}/{target_id:uuid}")
async def unlike_target(
    target_type: TargetType,
    target_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    like_service: Annotated[LikeService, Depends(get_like_service)],
) -> dict[str, str]:
    artist_id = _require_artist_id(current_user)
    await like_service.unlike(
        artist_id=artist_id,
        target_type=target_type,
        target_id=target_id,
    )
    return {"detail": "Like removed successfully"}


def _require_artist_id(current_user: UserDTO) -> UUID:
    if current_user.artist_id is None:
        raise ArtistNotFoundError
    return current_user.artist_id
