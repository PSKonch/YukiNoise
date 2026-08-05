import asyncio
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from yn.modules.auth.errors import InvalidRefreshTokenError
from yn.modules.auth.service import AuthService


def make_auth_service(
    *,
    stored_token: object | None,
    revoked: bool = True,
) -> tuple[AuthService, AsyncMock]:
    refresh_tokens = SimpleNamespace(
        get_active_by_hash=AsyncMock(return_value=stored_token),
        revoke=AsyncMock(return_value=revoked),
    )
    uow = SimpleNamespace(refresh_tokens=refresh_tokens, commit=AsyncMock())
    security = SimpleNamespace(
        token_processor=SimpleNamespace(
            hash_refresh_token=lambda _: "hashed-refresh-token"
        )
    )
    service = AuthService(
        uow=cast(Any, uow),
        security=cast(Any, security),
    )
    return service, refresh_tokens.revoke


def test_logout_rejects_unknown_refresh_token() -> None:
    service, revoke = make_auth_service(stored_token=None)

    with pytest.raises(InvalidRefreshTokenError):
        asyncio.run(service.logout("unknown-token"))

    revoke.assert_not_awaited()


def test_logout_rejects_refresh_token_that_cannot_be_revoked() -> None:
    stored_token = SimpleNamespace(id=uuid4())
    service, revoke = make_auth_service(stored_token=stored_token, revoked=False)

    with pytest.raises(InvalidRefreshTokenError):
        asyncio.run(service.logout("already-revoked-token"))

    revoke.assert_awaited_once_with(stored_token.id)


def test_logout_revokes_active_refresh_token() -> None:
    stored_token = SimpleNamespace(id=uuid4())
    service, revoke = make_auth_service(stored_token=stored_token)

    asyncio.run(service.logout("active-token"))

    revoke.assert_awaited_once_with(stored_token.id)
    cast(AsyncMock, service.uow.commit).assert_awaited_once()
