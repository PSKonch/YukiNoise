from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.auth.auth import get_current_user
from yn.modules.posts.deps import get_post_read_service, get_post_service
from yn.modules.posts.errors import (
    EmptyPostUpdateError,
)
from yn.modules.posts.schemas import PostCreate, PostRead, PostUpdate
from yn.modules.posts.service import PostService
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/posts", tags=["posts"])


# Public read
@router.get("/search")
async def search_posts(
    query: str,
    post_service: Annotated[PostService, Depends(get_post_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[PostRead]:
    posts = await post_service.full_text_search_posts(
        query,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [PostRead.model_validate(post, from_attributes=True) for post in posts]


@router.get("/")
async def get_posts(
    post_service: Annotated[PostService, Depends(get_post_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[PostRead]:
    posts = await post_service.get_posts(
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [PostRead.model_validate(post, from_attributes=True) for post in posts]


@router.get("/{post_id:uuid}")
async def get_post_by_id(
    post_service: Annotated[PostService, Depends(get_post_read_service)],
    post_id: UUID,
) -> PostRead:
    post = await post_service.get_post_by_id(post_id)
    return PostRead.model_validate(post, from_attributes=True)


# Owner write
@router.post("/")
async def create_post(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
    payload: PostCreate,
) -> PostRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    post = await post_service.create_post(
        artist_id=current_user.artist_id,
        title=payload.title,
        content=payload.content,
    )
    return PostRead.model_validate(post, from_attributes=True)


# Owner read
@router.get("/me")
async def get_owned_posts(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[PostRead]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    posts = await post_service.get_owned_posts(
        artist_id=current_user.artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [PostRead.model_validate(post, from_attributes=True) for post in posts]


@router.get("/me/{post_id:uuid}")
async def get_owned_post_by_id(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
    post_id: UUID,
) -> PostRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    post = await post_service.get_owned_post_by_id(
        post_id=post_id,
        artist_id=current_user.artist_id,
    )
    return PostRead.model_validate(post, from_attributes=True)


@router.put("/{post_id:uuid}")
async def update_post(
    post_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
    payload: PostUpdate,
) -> dict[str, str]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    if payload.title is None and payload.content is None:
        raise EmptyPostUpdateError

    await post_service.update_post(
        post_id=post_id,
        artist_id=current_user.artist_id,
        title=payload.title,
        content=payload.content,
    )

    return {"detail": "Post updated successfully"}


@router.delete("/{post_id:uuid}")
async def delete_post(
    post_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
) -> dict[str, str]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    await post_service.delete_post(post_id=post_id, artist_id=current_user.artist_id)

    return {"detail": "Post deleted successfully"}
