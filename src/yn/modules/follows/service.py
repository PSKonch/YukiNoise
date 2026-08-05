from uuid import UUID

from yn.modules.artists.dto import ArtistDTO
from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.follows.dto import FollowDTO
from yn.modules.follows.errors import (
    FollowAlreadyExistsError,
    FollowNotFoundError,
    SelfFollowError,
)
from yn.shared.unit_of_work import UnitOfWork


class FollowService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_followers(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[ArtistDTO]:
        await self._ensure_artist_exists(artist_id)
        artists = await self.uow.follows.get_followers(
            followed_id=artist_id,
            limit=limit,
            offset=offset,
        )
        return [ArtistDTO.from_orm(artist) for artist in artists]

    async def get_following(
        self, artist_id: UUID, *, limit: int, offset: int
    ) -> list[ArtistDTO]:
        await self._ensure_artist_exists(artist_id)
        artists = await self.uow.follows.get_following(
            follower_id=artist_id,
            limit=limit,
            offset=offset,
        )
        return [ArtistDTO.from_orm(artist) for artist in artists]

    async def is_following(self, follower_id: UUID, followed_id: UUID) -> bool:
        if follower_id == followed_id:
            return False
        await self._ensure_artist_exists(followed_id)
        return await self.uow.follows.is_following(
            follower_id=follower_id,
            followed_id=followed_id,
        )

    async def follow(self, follower_id: UUID, followed_id: UUID) -> FollowDTO:
        self._ensure_not_self(follower_id, followed_id)
        await self._ensure_artist_exists(followed_id)
        follow = await self.uow.follows.create(
            follower_id=follower_id,
            followed_id=followed_id,
        )
        if follow is None:
            raise FollowAlreadyExistsError
        await self.uow.commit()
        return FollowDTO.from_orm(follow)

    async def unfollow(self, follower_id: UUID, followed_id: UUID) -> None:
        self._ensure_not_self(follower_id, followed_id)
        deleted = await self.uow.follows.delete(
            follower_id=follower_id,
            followed_id=followed_id,
        )
        if not deleted:
            raise FollowNotFoundError
        await self.uow.commit()

    async def _ensure_artist_exists(self, artist_id: UUID) -> None:
        artist = await self.uow.artists.get_artist_by_id(artist_id)
        if artist is None or getattr(artist, "deleted_at", None) is not None:
            raise ArtistNotFoundError

    @staticmethod
    def _ensure_not_self(follower_id: UUID, followed_id: UUID) -> None:
        if follower_id == followed_id:
            raise SelfFollowError
