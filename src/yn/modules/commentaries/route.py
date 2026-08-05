from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.auth.auth import get_current_user
from yn.modules.commentaries.deps import (
    get_commentary_read_service,
    get_commentary_service,
)
from yn.modules.commentaries.schemas import (
    CommentaryCreate,
    CommentaryRead,
    CommentaryUpdate,
)
from yn.modules.commentaries.service import CommentaryService
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter(tags=["commentaries"])


@router.get("/posts/{post_id:uuid}/commentaries")
async def get_commentaries_by_post_id(
    post_id: UUID,
    commentary_service: Annotated[
        CommentaryService, Depends(get_commentary_read_service)
    ],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[CommentaryRead]:
    commentaries = await commentary_service.get_commentaries_by_post_id(
        post_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        CommentaryRead.model_validate(commentary, from_attributes=True)
        for commentary in commentaries
    ]


@router.get("/commentaries/{commentary_id:uuid}")
async def get_commentary_by_id(
    commentary_id: UUID,
    commentary_service: Annotated[
        CommentaryService, Depends(get_commentary_read_service)
    ],
) -> CommentaryRead:
    commentary = await commentary_service.get_commentary_by_id(commentary_id)
    return CommentaryRead.model_validate(commentary, from_attributes=True)


@router.post(
    "/posts/{post_id:uuid}/commentaries",
    status_code=status.HTTP_201_CREATED,
)
async def create_commentary(
    post_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    commentary_service: Annotated[CommentaryService, Depends(get_commentary_service)],
    payload: CommentaryCreate,
) -> CommentaryRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    commentary = await commentary_service.create_commentary(
        artist_id=current_user.artist_id,
        post_id=post_id,
        content=payload.content,
        commentary_id=payload.commentary_id,
    )
    return CommentaryRead.model_validate(commentary, from_attributes=True)


@router.put("/commentaries/{commentary_id:uuid}")
async def update_commentary(
    commentary_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    commentary_service: Annotated[CommentaryService, Depends(get_commentary_service)],
    payload: CommentaryUpdate,
) -> CommentaryRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    commentary = await commentary_service.update_commentary(
        commentary_id=commentary_id,
        artist_id=current_user.artist_id,
        content=payload.content,
    )
    return CommentaryRead.model_validate(commentary, from_attributes=True)


@router.delete(
    "/commentaries/{commentary_id:uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_commentary(
    commentary_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    commentary_service: Annotated[CommentaryService, Depends(get_commentary_service)],
) -> None:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    await commentary_service.delete_commentary(
        commentary_id=commentary_id,
        artist_id=current_user.artist_id,
    )
