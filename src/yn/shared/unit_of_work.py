from types import TracebackType
from typing import TYPE_CHECKING, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from yn.shared.database import get_primary_session, get_replica_session

if TYPE_CHECKING:
    from yn.modules.artists.repository import ArtistRepository
    from yn.modules.auth.repository import RefreshTokenRepository
    from yn.modules.commentaries.repository import CommentaryRepository
    from yn.modules.follows.repository import FollowRepository
    from yn.modules.likes.repository import LikeRepository
    from yn.modules.playlists.repository import PlaylistsRepository
    from yn.modules.posts.repository import PostRepository
    from yn.modules.releases.repository import ReleaseRepository
    from yn.modules.tracks.repository import TrackRepository
    from yn.modules.users.repository import UserRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._users_repo: "UserRepository | None" = None
        self._artists_repo: "ArtistRepository | None" = None
        self._refresh_tokens_repo: "RefreshTokenRepository | None" = None
        self._commentaries_repo: "CommentaryRepository | None" = None
        self._follows_repo: "FollowRepository | None" = None
        self._likes_repo: "LikeRepository | None" = None
        self._playlists_repo: "PlaylistsRepository | None" = None
        self._posts_repo: "PostRepository | None" = None
        self._releases_repo: "ReleaseRepository | None" = None
        self._tracks_repo: "TrackRepository | None" = None

    @property
    def users(self) -> "UserRepository":
        if self._users_repo is None:
            from importlib import import_module

            repo_mod = import_module("yn.modules.users.repository")
            UserRepository = getattr(repo_mod, "UserRepository")
            self._users_repo = UserRepository(self._session)
        return self._users_repo

    @property
    def artists(self) -> "ArtistRepository":
        if self._artists_repo is None:
            from importlib import import_module

            repo_mod = import_module("yn.modules.artists.repository")
            ArtistRepository = getattr(repo_mod, "ArtistRepository")
            self._artists_repo = ArtistRepository(self._session)
        return self._artists_repo

    @property
    def refresh_tokens(self) -> "RefreshTokenRepository":
        if self._refresh_tokens_repo is None:
            from importlib import import_module

            repo_mod = import_module("yn.modules.auth.repository")
            RefreshTokenRepository = getattr(repo_mod, "RefreshTokenRepository")
            self._refresh_tokens_repo = RefreshTokenRepository(self._session)
        return self._refresh_tokens_repo

    @property
    def commentaries(self) -> "CommentaryRepository":
        if self._commentaries_repo is None:
            from importlib import import_module

            repo_mod = import_module("yn.modules.commentaries.repository")
            CommentaryRepository = getattr(repo_mod, "CommentaryRepository")
            self._commentaries_repo = CommentaryRepository(self._session)
        return self._commentaries_repo

    @property
    def follows(self) -> "FollowRepository":
        if self._follows_repo is None:
            from importlib import import_module

            repo_mod = import_module("yn.modules.follows.repository")
            FollowRepository = getattr(repo_mod, "FollowRepository")
            self._follows_repo = FollowRepository(self._session)
        return self._follows_repo

    @property
    def likes(self) -> "LikeRepository":
        if self._likes_repo is None:
            from importlib import import_module

            repo_mod = import_module("yn.modules.likes.repository")
            LikeRepository = getattr(repo_mod, "LikeRepository")
            self._likes_repo = LikeRepository(self._session)
        return self._likes_repo

    @property
    def playlists(self) -> "PlaylistsRepository":
        if self._playlists_repo is None:
            from importlib import import_module

            repo_mod = import_module("yn.modules.playlists.repository")
            PlaylistsRepository = getattr(repo_mod, "PlaylistsRepository")
            self._playlists_repo = PlaylistsRepository(self._session)
        return self._playlists_repo

    @property
    def posts(self) -> "PostRepository":
        if self._posts_repo is None:
            from importlib import import_module

            repo_mod = import_module("yn.modules.posts.repository")
            PostRepository = getattr(repo_mod, "PostRepository")
            self._posts_repo = PostRepository(self._session)
        return self._posts_repo

    @property
    def releases(self) -> "ReleaseRepository":
        if self._releases_repo is None:
            from importlib import import_module

            repo_mod = import_module("yn.modules.releases.repository")
            ReleaseRepository = getattr(repo_mod, "ReleaseRepository")
            self._releases_repo = ReleaseRepository(self._session)
        return self._releases_repo

    @property
    def tracks(self) -> "TrackRepository":
        if self._tracks_repo is None:
            from importlib import import_module

            repo_mod = import_module("yn.modules.tracks.repository")
            TrackRepository = getattr(repo_mod, "TrackRepository")
            self._tracks_repo = TrackRepository(self._session)
        return self._tracks_repo

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc:
            await self._session.rollback()
        else:
            try:
                await self._session.commit()
            except Exception:
                await self._session.rollback()
                raise

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()


class ReadOnlyUnitOfWork(UnitOfWork):
    async def __aenter__(self) -> "ReadOnlyUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._session.rollback()

    async def commit(self) -> None:
        raise RuntimeError("Read-only unit of work cannot commit.")


async def get_uow() -> AsyncGenerator["UnitOfWork", None]:
    async for session in get_primary_session():
        async with UnitOfWork(session) as uow:
            yield uow


async def get_read_uow() -> AsyncGenerator["ReadOnlyUnitOfWork", None]:
    async for session in get_replica_session():
        async with ReadOnlyUnitOfWork(session) as uow:
            yield uow
