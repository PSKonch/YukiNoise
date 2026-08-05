from uuid import UUID

from yn.modules.commentaries.dto import CommentaryDTO
from yn.modules.commentaries.errors import (
    CommentaryNotFoundError,
    CommentaryParentNotFoundError,
    CommentaryParentPostMismatchError,
)
from yn.modules.posts.errors import PostNotFoundError
from yn.shared.unit_of_work import UnitOfWork


class CommentaryService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_commentaries_by_post_id(
        self, post_id: UUID, *, limit: int, offset: int
    ) -> list[CommentaryDTO]:
        await self._ensure_post_exists(post_id)
        commentaries = await self.uow.commentaries.get_commentaries_by_post_id(
            post_id,
            limit=limit,
            offset=offset,
        )
        return [CommentaryDTO.from_orm(commentary) for commentary in commentaries]

    async def get_commentary_by_id(self, commentary_id: UUID) -> CommentaryDTO:
        commentary = await self.uow.commentaries.get_commentary_by_id(commentary_id)
        if commentary is None:
            raise CommentaryNotFoundError
        return CommentaryDTO.from_orm(commentary)

    async def create_commentary(
        self,
        *,
        artist_id: UUID,
        post_id: UUID,
        content: str,
        commentary_id: UUID | None = None,
    ) -> CommentaryDTO:
        await self._ensure_post_exists(post_id)
        if commentary_id is not None:
            parent = await self.uow.commentaries.get_commentary_by_id(commentary_id)
            if parent is None:
                raise CommentaryParentNotFoundError
            if parent.post_id != post_id:
                raise CommentaryParentPostMismatchError

        commentary = await self.uow.commentaries.create(
            artist_id=artist_id,
            post_id=post_id,
            content=content,
            commentary_id=commentary_id,
        )
        return CommentaryDTO.from_orm(commentary)

    async def update_commentary(
        self, *, commentary_id: UUID, artist_id: UUID, content: str
    ) -> CommentaryDTO:
        commentary = await self.uow.commentaries.update(
            commentary_id=commentary_id,
            artist_id=artist_id,
            content=content,
        )
        if commentary is None:
            raise CommentaryNotFoundError
        return CommentaryDTO.from_orm(commentary)

    async def delete_commentary(self, *, commentary_id: UUID, artist_id: UUID) -> None:
        deleted = await self.uow.commentaries.soft_delete(
            commentary_id=commentary_id,
            artist_id=artist_id,
        )
        if not deleted:
            raise CommentaryNotFoundError

    async def _ensure_post_exists(self, post_id: UUID) -> None:
        if await self.uow.posts.get_post_by_id(post_id) is None:
            raise PostNotFoundError
