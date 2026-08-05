from uuid import UUID

from yn.modules.likes.dto import LikeDTO
from yn.modules.likes.enums import TargetType
from yn.modules.likes.errors import (
    LikeAlreadyExistsError,
    LikeNotFoundError,
    LikeTargetNotFoundError,
)
from yn.shared.unit_of_work import UnitOfWork


class LikeService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def is_liked(
        self, artist_id: UUID, target_type: TargetType, target_id: UUID
    ) -> bool:
        await self._ensure_target_exists(target_type, target_id)
        return await self.uow.likes.is_liked(
            artist_id=artist_id,
            target_type=target_type,
            target_id=target_id,
        )

    async def like(
        self, artist_id: UUID, target_type: TargetType, target_id: UUID
    ) -> LikeDTO:
        await self._ensure_target_exists(target_type, target_id)
        like = await self.uow.likes.create(
            artist_id=artist_id,
            target_type=target_type,
            target_id=target_id,
        )
        if like is None:
            raise LikeAlreadyExistsError
        await self.uow.commit()
        return LikeDTO.from_orm(like)

    async def unlike(
        self, artist_id: UUID, target_type: TargetType, target_id: UUID
    ) -> None:
        deleted = await self.uow.likes.delete(
            artist_id=artist_id,
            target_type=target_type,
            target_id=target_id,
        )
        if not deleted:
            raise LikeNotFoundError
        await self.uow.commit()

    async def _ensure_target_exists(
        self, target_type: TargetType, target_id: UUID
    ) -> None:
        if not await self.uow.likes.target_exists(target_type, target_id):
            raise LikeTargetNotFoundError
