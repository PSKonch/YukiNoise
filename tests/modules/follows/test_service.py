import asyncio
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.follows.errors import (
    FollowAlreadyExistsError,
    FollowNotFoundError,
    SelfFollowError,
)
from yn.modules.follows.service import FollowService


def make_service(
    *,
    target: object | None,
    created_follow: object | None = None,
    deleted: bool = True,
) -> tuple[FollowService, SimpleNamespace]:
    repositories = SimpleNamespace(
        artists=SimpleNamespace(get_artist_by_id=AsyncMock(return_value=target)),
        follows=SimpleNamespace(
            create=AsyncMock(return_value=created_follow),
            delete=AsyncMock(return_value=deleted),
            is_following=AsyncMock(return_value=True),
        ),
        commit=AsyncMock(),
    )
    return FollowService(cast(Any, repositories)), repositories


def test_follow_creates_relationship() -> None:
    follower_id = uuid4()
    followed_id = uuid4()
    follow_id = uuid4()
    follow = SimpleNamespace(
        id=follow_id,
        follower_id=follower_id,
        followed_id=followed_id,
        created_at=datetime.now(),
    )
    service, repositories = make_service(
        target=SimpleNamespace(deleted_at=None),
        created_follow=follow,
    )

    result = asyncio.run(service.follow(follower_id, followed_id))

    assert result.id == follow_id
    repositories.follows.create.assert_awaited_once_with(
        follower_id=follower_id,
        followed_id=followed_id,
    )
    repositories.commit.assert_awaited_once()


def test_follow_rejects_duplicate() -> None:
    service, repositories = make_service(target=SimpleNamespace(deleted_at=None))

    with pytest.raises(FollowAlreadyExistsError):
        asyncio.run(service.follow(uuid4(), uuid4()))

    repositories.commit.assert_not_awaited()


def test_follow_rejects_self_without_querying_database() -> None:
    artist_id = uuid4()
    service, repositories = make_service(target=SimpleNamespace(deleted_at=None))

    with pytest.raises(SelfFollowError):
        asyncio.run(service.follow(artist_id, artist_id))

    repositories.artists.get_artist_by_id.assert_not_awaited()
    repositories.follows.create.assert_not_awaited()


def test_own_follow_status_is_false_without_querying_database() -> None:
    artist_id = uuid4()
    service, repositories = make_service(target=SimpleNamespace(deleted_at=None))

    result = asyncio.run(service.is_following(artist_id, artist_id))

    assert result is False
    repositories.artists.get_artist_by_id.assert_not_awaited()
    repositories.follows.is_following.assert_not_awaited()


@pytest.mark.parametrize("target", [None, SimpleNamespace(deleted_at=datetime.now())])
def test_follow_rejects_missing_or_deleted_artist(target: object | None) -> None:
    service, repositories = make_service(target=target)

    with pytest.raises(ArtistNotFoundError):
        asyncio.run(service.follow(uuid4(), uuid4()))

    repositories.follows.create.assert_not_awaited()


def test_unfollow_rejects_missing_relationship() -> None:
    service, _ = make_service(
        target=SimpleNamespace(deleted_at=None),
        deleted=False,
    )

    with pytest.raises(FollowNotFoundError):
        asyncio.run(service.unfollow(uuid4(), uuid4()))
