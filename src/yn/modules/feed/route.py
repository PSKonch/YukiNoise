from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from yn.modules.auth.auth import get_current_user
from yn.modules.releases.dto import ReleaseWithTracksAndAuthorDTO
from yn.modules.releases.schemas import ReleaseWithTracksAndAuthorRead
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params
from yn.shared.unit_of_work import UnitOfWork, get_uow

router = APIRouter(prefix="/me/feed", tags=["feed"])


class ReleaseFeedPage(BaseModel):
    items: list[ReleaseWithTracksAndAuthorRead]
    has_more: bool


@router.get("/releases")
async def following_releases(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> ReleaseFeedPage:
    # Reading the primary makes an immediately followed/unfollowed artist visible
    # consistently, even while the replica is catching up.
    if current_user.artist_id is None:
        return ReleaseFeedPage(items=[], has_more=False)
    releases = await uow.releases.get_following_releases(
        current_user.artist_id,
        limit=pagination.limit + 1,
        offset=pagination.offset,
    )
    return ReleaseFeedPage(
        items=[
            ReleaseWithTracksAndAuthorRead.model_validate(
                ReleaseWithTracksAndAuthorDTO.from_orm(release),
                from_attributes=True,
            )
            for release in releases[: pagination.limit]
        ],
        has_more=len(releases) > pagination.limit,
    )
