import asyncio
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from yn.modules.likes.enums import TargetType
from yn.modules.likes.errors import (
    LikeAlreadyExistsError,
    LikeNotFoundError,
    LikeTargetNotFoundError,
)
from yn.modules.likes.service import LikeService


def make_service(
    *,
    target_exists: bool = True,
    created_like: object | None = None,
    deleted: bool = True,
) -> tuple[LikeService, SimpleNamespace]:
    likes = SimpleNamespace(
        target_exists=AsyncMock(return_value=target_exists),
        is_liked=AsyncMock(return_value=True),
        create=AsyncMock(return_value=created_like),
        delete=AsyncMock(return_value=deleted),
    )
    uow = SimpleNamespace(likes=likes, commit=AsyncMock())
    return LikeService(cast(Any, uow)), likes


def test_like_creates_relationship() -> None:
    artist_id = uuid4()
    target_id = uuid4()
    like_id = uuid4()
    like = SimpleNamespace(
        id=like_id,
        artist_id=artist_id,
        target_type=TargetType.TRACK,
        target_id=target_id,
        created_at=datetime.now(),
    )
    service, repository = make_service(created_like=like)

    result = asyncio.run(service.like(artist_id, TargetType.TRACK, target_id))

    assert result.id == like_id
    repository.create.assert_awaited_once_with(
        artist_id=artist_id,
        target_type=TargetType.TRACK,
        target_id=target_id,
    )
    cast(AsyncMock, service.uow.commit).assert_awaited_once()


def test_like_rejects_missing_target() -> None:
    service, repository = make_service(target_exists=False)

    with pytest.raises(LikeTargetNotFoundError):
        asyncio.run(service.like(uuid4(), TargetType.POST, uuid4()))

    repository.create.assert_not_awaited()


def test_like_rejects_duplicate() -> None:
    service, _ = make_service()

    with pytest.raises(LikeAlreadyExistsError):
        asyncio.run(service.like(uuid4(), TargetType.RELEASE, uuid4()))

    cast(AsyncMock, service.uow.commit).assert_not_awaited()


def test_unlike_rejects_missing_like() -> None:
    service, _ = make_service(deleted=False)

    with pytest.raises(LikeNotFoundError):
        asyncio.run(service.unlike(uuid4(), TargetType.PLAYLIST, uuid4()))
