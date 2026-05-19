from uuid import UUID

from sqlalchemy.exc import IntegrityError

from yn.modules.posts.dto import PostDTO
from yn.modules.posts.errors import (
    EmptyPostUpdateError,
    PostConflictError,
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
        try:
            post = await self.uow.posts.create(
                profile_id=profile_id, title=title, content=content
            )
        except IntegrityError as exc:
            raise PostConflictError from exc
        return PostDTO.from_orm(post)

    async def update_post(
        self,
        post_id: UUID,
        title: str | None = None,
        content: str | None = None,
    ) -> bool:
        if title is None and content is None:
            raise EmptyPostUpdateError

        updated = await self.uow.posts.update(
            post_id=post_id, title=title, content=content
        )
        if not updated:
            raise PostNotFoundError
        return updated

    async def delete_post(self, post_id: UUID) -> bool:
        deleted = await self.uow.posts.hard_delete(post_id)
        if not deleted:
            raise PostNotFoundError
        return deleted

    async def full_text_search_posts(self, query: str) -> list[PostDTO]:
        posts = await self.uow.posts.full_text_search_posts(query)
        return [PostDTO.from_orm(post) for post in posts]

    async def get_posts(self) -> list[PostDTO]:
        posts = await self.uow.posts.get_posts()
        return [PostDTO.from_orm(post) for post in posts]
