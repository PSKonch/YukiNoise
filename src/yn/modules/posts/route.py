from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from yn.modules.posts.deps import get_post_service
from yn.modules.posts.errors import (
    EmptyPostUpdateError,
    PostNotFoundError,
)
from yn.modules.posts.schemas import PostCreate, PostRead, PostUpdate
from yn.modules.posts.service import PostService
from yn.modules.users.auth import get_current_user
from yn.modules.users.dto import UserDTO

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("/")
async def create_post(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
    payload: PostCreate,
) -> PostRead:
    post = await post_service.create_post(
        profile_id=current_user.profile_id,
        title=payload.title,
        content=payload.content,
    )
    return PostRead.model_validate(post, from_attributes=True)


@router.put("/{post_id}")
async def update_post(
    post_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
    payload: PostUpdate,
) -> dict[str, str]:
    if payload.title is None and payload.content is None:
        raise EmptyPostUpdateError

    try:
        await post_service.update_post(
            post_id=post_id, title=payload.title, content=payload.content
        )
    except PostNotFoundError:
        raise PostNotFoundError

    return {"detail": "Post updated successfully"}


@router.delete("/{post_id}")
async def delete_post(
    post_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
) -> dict[str, str]:
    try:
        await post_service.delete_post(post_id=post_id)
    except PostNotFoundError:
        raise PostNotFoundError

    return {"detail": "Post deleted successfully"}


@router.get("/search")
async def search_posts(
    query: str,
    post_service: Annotated[PostService, Depends(get_post_service)],
) -> list[PostRead]:
    posts = await post_service.full_text_search_posts(query)
    return [PostRead.model_validate(post, from_attributes=True) for post in posts]


@router.get("/")
async def get_posts(
    post_service: Annotated[PostService, Depends(get_post_service)],
) -> list[PostRead]:
    posts = await post_service.get_posts()
    return [PostRead.model_validate(post, from_attributes=True) for post in posts]
