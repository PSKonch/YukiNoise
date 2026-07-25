import asyncio

import pytest

from yn import main
from yn.shared.database import ReplicaStatus


def test_readiness_is_healthy_for_a_current_replica(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def get_status() -> ReplicaStatus:
        return ReplicaStatus(is_replica=True, lag_bytes=0)

    monkeypatch.setattr(main, "get_replica_status", get_status)

    response = asyncio.run(main.readiness_check())

    assert response.status_code == 200
    assert b'"is_replica":true' in response.body


def test_readiness_rejects_a_promoted_replica(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def get_status() -> ReplicaStatus:
        return ReplicaStatus(is_replica=False, lag_bytes=None)

    monkeypatch.setattr(main, "get_replica_status", get_status)

    response = asyncio.run(main.readiness_check())

    assert response.status_code == 503


def test_readiness_rejects_an_unreachable_replica(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def get_status() -> ReplicaStatus:
        raise OSError("connection refused")

    monkeypatch.setattr(main, "get_replica_status", get_status)

    response = asyncio.run(main.readiness_check())

    assert response.status_code == 503
    assert b'"replica":"unreachable"' in response.body
