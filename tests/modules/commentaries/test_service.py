import asyncio
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from yn.modules.commentaries.errors import (
    CommentaryNotFoundError,
    CommentaryParentNotFoundError,
    CommentaryParentPostMismatchError,
)
from yn.modules.commentaries.service import CommentaryService
from yn.modules.posts.errors import PostNotFoundError


def commentary_entity(
    *,
    post_id: UUID,
    artist_id: UUID | None = None,
    commentary_id: UUID | None = None,
    content: str = "Comment",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        artist_id=artist_id or uuid4(),
        post_id=post_id,
        commentary_id=commentary_id,
        content=content,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        deleted_at=None,
    )


def make_service(
    *,
    post: object | None = None,
    parent: object | None = None,
    created: object | None = None,
    updated: object | None = None,
    deleted: bool = True,
) -> tuple[CommentaryService, SimpleNamespace]:
    commentaries = SimpleNamespace(
        get_commentary_by_id=AsyncMock(return_value=parent),
        get_commentaries_by_post_id=AsyncMock(return_value=[]),
        create=AsyncMock(return_value=created),
        update=AsyncMock(return_value=updated),
        soft_delete=AsyncMock(return_value=deleted),
    )
    uow = SimpleNamespace(
        posts=SimpleNamespace(get_post_by_id=AsyncMock(return_value=post)),
        commentaries=commentaries,
    )
    return CommentaryService(cast(Any, uow)), commentaries


def test_create_commentary() -> None:
    post_id = uuid4()
    artist_id = uuid4()
    created = commentary_entity(post_id=post_id, artist_id=artist_id)
    service, repository = make_service(
        post=SimpleNamespace(id=post_id), created=created
    )

    result = asyncio.run(
        service.create_commentary(
            artist_id=artist_id,
            post_id=post_id,
            content="Comment",
        )
    )

    assert result.id == created.id
    repository.create.assert_awaited_once_with(
        artist_id=artist_id,
        post_id=post_id,
        content="Comment",
        commentary_id=None,
    )


def test_create_commentary_rejects_missing_post() -> None:
    service, repository = make_service()

    with pytest.raises(PostNotFoundError):
        asyncio.run(
            service.create_commentary(
                artist_id=uuid4(), post_id=uuid4(), content="Comment"
            )
        )

    repository.create.assert_not_awaited()


def test_reply_rejects_missing_parent() -> None:
    service, repository = make_service(post=SimpleNamespace(id=uuid4()))

    with pytest.raises(CommentaryParentNotFoundError):
        asyncio.run(
            service.create_commentary(
                artist_id=uuid4(),
                post_id=uuid4(),
                commentary_id=uuid4(),
                content="Reply",
            )
        )

    repository.create.assert_not_awaited()


def test_reply_rejects_parent_from_another_post() -> None:
    post_id = uuid4()
    parent = commentary_entity(post_id=uuid4())
    service, repository = make_service(
        post=SimpleNamespace(id=post_id),
        parent=parent,
    )

    with pytest.raises(CommentaryParentPostMismatchError):
        asyncio.run(
            service.create_commentary(
                artist_id=uuid4(),
                post_id=post_id,
                commentary_id=parent.id,
                content="Reply",
            )
        )

    repository.create.assert_not_awaited()


def test_update_rejects_missing_or_foreign_commentary() -> None:
    service, _ = make_service()

    with pytest.raises(CommentaryNotFoundError):
        asyncio.run(
            service.update_commentary(
                commentary_id=uuid4(), artist_id=uuid4(), content="Updated"
            )
        )


def test_delete_rejects_missing_or_foreign_commentary() -> None:
    service, _ = make_service(deleted=False)

    with pytest.raises(CommentaryNotFoundError):
        asyncio.run(service.delete_commentary(commentary_id=uuid4(), artist_id=uuid4()))
