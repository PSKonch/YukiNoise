import asyncio
from copy import deepcopy
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from yn.modules.playback.errors import PlaybackDeviceConflictError
from yn.modules.playback.schemas import PlaybackContext, PlaybackContextType, RepeatMode
from yn.modules.playback.service import PlaybackService, covered_ms, merge_intervals
from yn.modules.tracks.model import Track


class MemoryPlaybackRepository:
    def __init__(self) -> None:
        self.state: dict[str, Any] | None = None

    async def get(self, _: UUID) -> dict[str, Any] | None:
        return deepcopy(self.state)

    async def compare_and_set(
        self, _: UUID, expected_revision: int, state: dict[str, Any]
    ) -> bool:
        current_revision = self.state["revision"] if self.state else -1
        if current_revision != expected_revision:
            return False
        self.state = deepcopy(state)
        return True

    async def delete(self, _: UUID) -> bool:
        existed = self.state is not None
        self.state = None
        return existed


def track(number: int, duration_seconds: int = 120) -> Track:
    return Track(
        id=uuid4(),
        release_id=uuid4(),
        title=f"Track {number}",
        duration_seconds=duration_seconds,
        track_number_in_release=number,
        path=f"{number}.mp3",
        genres=[],
    )


def service_with_tracks(
    items: list[Track],
) -> tuple[PlaybackService, MemoryPlaybackRepository]:
    tracks = SimpleNamespace(
        get_public_tracks_for_release=lambda _: asyncio.sleep(0, result=items),
        increment_play_count=lambda _: asyncio.sleep(0, result=True),
    )
    uow = SimpleNamespace(tracks=tracks, commit=lambda: asyncio.sleep(0))
    repository = MemoryPlaybackRepository()
    return PlaybackService(cast(Any, uow), cast(Any, repository)), repository


def test_merge_intervals_counts_only_the_union() -> None:
    intervals = merge_intervals([[0, 30_000]], (90_000, 120_000))
    assert intervals == [[0, 30_000], [90_000, 120_000]]
    assert covered_ms(intervals) == 60_000
    assert covered_ms(merge_intervals(intervals, (20_000, 100_000))) == 120_000


def test_context_queue_starts_at_requested_track_and_repeats() -> None:
    first, second = track(1), track(2)
    service, _ = service_with_tracks([first, second])
    user_id, device_id, release_id = uuid4(), uuid4(), uuid4()

    state = asyncio.run(
        service.play(
            user_id=user_id,
            artist_id=None,
            device_id=device_id,
            context=PlaybackContext(type=PlaybackContextType.RELEASE, id=release_id),
            offset_track_id=second.id,
            position_ms=0,
        )
    )
    assert state.current_track.id == second.id
    asyncio.run(service.set_repeat(user_id, device_id, RepeatMode.CONTEXT))
    state = asyncio.run(service.next(user_id, device_id))
    assert state.current_track.id == first.id


def test_non_active_device_cannot_control_player() -> None:
    service, _ = service_with_tracks([track(1)])
    user_id, device_id = uuid4(), uuid4()
    asyncio.run(
        service.play(
            user_id=user_id,
            artist_id=None,
            device_id=device_id,
            context=PlaybackContext(type=PlaybackContextType.RELEASE, id=uuid4()),
            offset_track_id=None,
            position_ms=0,
        )
    )
    with pytest.raises(PlaybackDeviceConflictError):
        asyncio.run(service.pause(user_id, uuid4()))


def test_disjoint_halves_count_once() -> None:
    item = track(1, duration_seconds=120)
    increment = AsyncMock(return_value=True)
    tracks = SimpleNamespace(
        get_public_tracks_for_release=lambda _: asyncio.sleep(0, result=[item]),
        increment_play_count=increment,
    )
    uow = SimpleNamespace(tracks=tracks, commit=AsyncMock())
    repository = MemoryPlaybackRepository()
    service = PlaybackService(cast(Any, uow), cast(Any, repository))
    user_id, device_id = uuid4(), uuid4()
    initial = asyncio.run(
        service.play(
            user_id=user_id,
            artist_id=None,
            device_id=device_id,
            context=PlaybackContext(type=PlaybackContextType.RELEASE, id=uuid4()),
            offset_track_id=None,
            position_ms=0,
        )
    )
    assert repository.state is not None
    repository.state["last_heartbeat_ms"] -= 30_000
    first = asyncio.run(
        service.progress(
            user_id=user_id,
            device_id=device_id,
            session_id=initial.session_id,
            attempt_id=initial.attempt_id,
            sequence=1,
            position_ms=30_000,
        )
    )
    assert first.listened_ms == 30_000
    assert not first.counted

    asyncio.run(service.seek(user_id, device_id, 90_000))
    assert repository.state is not None
    repository.state["last_heartbeat_ms"] -= 30_000
    counted = asyncio.run(
        service.progress(
            user_id=user_id,
            device_id=device_id,
            session_id=initial.session_id,
            attempt_id=initial.attempt_id,
            sequence=2,
            position_ms=120_000,
        )
    )
    assert counted.listened_ms == 60_000
    assert counted.counted
    increment.assert_awaited_once_with(item.id)
