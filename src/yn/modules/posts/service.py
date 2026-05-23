from uuid import UUID

from yn.modules.posts.dto import PostDTO
from yn.modules.posts.errors import (
    EmptyPostUpdateError,
    PostNotFoundError,
)
from yn.shared.unit_of_work import UnitOfWork


class PostService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_post(
        self,
        profile_id: UUID,
        title: str,
        content: str,
    ) -> PostDTO:
        post = await self.uow.posts.create(
            profile_id=profile_id, title=title, content=content
        )
        return PostDTO.from_orm(post)

    async def update_post(
        self,
        post_id: UUID,
        profile_id: UUID,
        title: str | None = None,
        content: str | None = None,
    ) -> bool:
        if title is None and content is None:
            raise EmptyPostUpdateError

        updated = await self.uow.posts.update(
            post_id=post_id, profile_id=profile_id, title=title, content=content
        )
        if not updated:
            raise PostNotFoundError
        return updated

    async def delete_post(self, post_id: UUID, profile_id: UUID) -> bool:
        deleted = await self.uow.posts.hard_delete(post_id, profile_id)
        if not deleted:
            raise PostNotFoundError
        return deleted

    async def full_text_search_posts(
        self,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> list[PostDTO]:
        posts = await self.uow.posts.full_text_search_posts(
            query,
            limit=limit,
            offset=offset,
        )
        return [PostDTO.from_orm(post) for post in posts]

    async def get_posts(self, *, limit: int, offset: int) -> list[PostDTO]:
        posts = await self.uow.posts.get_posts(limit=limit, offset=offset)
        return [PostDTO.from_orm(post) for post in posts]
