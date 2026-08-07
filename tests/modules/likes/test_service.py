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
from yn.modules.likes.events import (
    LIKES_EVENTS_TOPIC,
    LikeCreatedEvent,
    LikeDeletedEvent,
)
from yn.modules.likes.service import LikeService
from yn.shared.outbox.publisher import OutboxPublisher


def make_service(
    *,
    target_exists: bool = True,
    created_like: object | None = None,
    deleted_like_id: object | None = None,
) -> tuple[LikeService, SimpleNamespace]:
    likes = SimpleNamespace(
        target_exists=AsyncMock(return_value=target_exists),
        is_liked=AsyncMock(return_value=True),
        create=AsyncMock(return_value=created_like),
        delete=AsyncMock(return_value=deleted_like_id),
    )
    uow = SimpleNamespace(
        likes=likes,
        outbox=SimpleNamespace(add=AsyncMock()),
        commit=AsyncMock(),
    )
    publisher = AsyncMock(spec=OutboxPublisher)
    return LikeService(cast(Any, uow), cast(OutboxPublisher, publisher)), likes


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
    outbox_add = cast(AsyncMock, service.uow.outbox.add)
    outbox_add.assert_awaited_once()
    outbox_call = outbox_add.await_args
    assert outbox_call is not None
    outbox_values = outbox_call.kwargs
    event = LikeCreatedEvent.model_validate(outbox_values["payload"])
    assert outbox_values == {
        "event_id": event.event_id,
        "topic": LIKES_EVENTS_TOPIC,
        "message_key": f"track:{target_id}",
        "event_type": "like.created",
        "version": 1,
        "payload": event.model_dump(mode="json"),
    }
    cast(AsyncMock, service.outbox_publisher).publish_now.assert_awaited_once_with(
        event.event_id
    )


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
    cast(AsyncMock, service.uow.outbox.add).assert_not_awaited()
    cast(AsyncMock, service.outbox_publisher).publish_now.assert_not_awaited()


def test_unlike_publishes_deleted_event() -> None:
    artist_id = uuid4()
    target_id = uuid4()
    like_id = uuid4()
    service, repository = make_service(deleted_like_id=like_id)

    asyncio.run(service.unlike(artist_id, TargetType.PLAYLIST, target_id))

    repository.delete.assert_awaited_once_with(
        artist_id=artist_id,
        target_type=TargetType.PLAYLIST,
        target_id=target_id,
    )
    cast(AsyncMock, service.uow.commit).assert_awaited_once()
    outbox_add = cast(AsyncMock, service.uow.outbox.add)
    outbox_add.assert_awaited_once()
    outbox_call = outbox_add.await_args
    assert outbox_call is not None
    outbox_values = outbox_call.kwargs
    event = LikeDeletedEvent.model_validate(outbox_values["payload"])
    assert event.like_id == like_id
    assert event.artist_id == artist_id
    assert event.target_type == TargetType.PLAYLIST
    assert event.target_id == target_id
    assert outbox_values == {
        "event_id": event.event_id,
        "topic": LIKES_EVENTS_TOPIC,
        "message_key": f"playlist:{target_id}",
        "event_type": "like.deleted",
        "version": 1,
        "payload": event.model_dump(mode="json"),
    }
    cast(AsyncMock, service.outbox_publisher).publish_now.assert_awaited_once_with(
        event.event_id
    )


def test_unlike_rejects_missing_like() -> None:
    service, _ = make_service()

    with pytest.raises(LikeNotFoundError):
        asyncio.run(service.unlike(uuid4(), TargetType.PLAYLIST, uuid4()))

    cast(AsyncMock, service.uow.commit).assert_not_awaited()
    cast(AsyncMock, service.uow.outbox.add).assert_not_awaited()
    cast(AsyncMock, service.outbox_publisher).publish_now.assert_not_awaited()
