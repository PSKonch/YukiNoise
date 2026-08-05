import asyncio
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

from yn.modules.users.service import UserService


def test_soft_delete_and_session_revocation_commit_together() -> None:
    async def run() -> None:
        user_id = uuid4()
        users = SimpleNamespace(soft_delete_user=AsyncMock())
        refresh_tokens = SimpleNamespace(revoke_all_for_user=AsyncMock())
        commit = AsyncMock()
        service = UserService(
            cast(
                Any,
                SimpleNamespace(
                    users=users,
                    refresh_tokens=refresh_tokens,
                    commit=commit,
                ),
            )
        )

        await service.soft_delete_current_user(user_id)

        users.soft_delete_user.assert_awaited_once_with(user_id)
        refresh_tokens.revoke_all_for_user.assert_awaited_once_with(user_id)
        commit.assert_awaited_once()

    asyncio.run(run())
