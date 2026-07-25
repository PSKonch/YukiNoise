import math
import time
from dataclasses import dataclass
from typing import Any, Sequence, cast
from uuid import UUID, uuid4

from prometheus_client import Counter, Histogram

from yn.modules.playback.errors import (
    PlaybackConflictError,
    PlaybackContextNotFoundError,
    PlaybackDeviceConflictError,
    PlaybackNotFoundError,
    PlaybackProgressRejectedError,
)
from yn.modules.playback.repository import PlaybackRepository
from yn.modules.playback.schemas import (
    PlaybackContext,
    PlaybackContextType,
    PlaybackQueueResponse,
    PlaybackStateResponse,
    PlaybackTrack,
    RepeatMode,
)
from yn.modules.tracks.model import Track
from yn.shared.unit_of_work import UnitOfWork

REJECTED_PROGRESS = Counter(
    "yukinoise_playback_progress_rejected_total", "Rejected playback heartbeats"
)
DEVICE_TAKEOVERS = Counter(
    "yukinoise_playback_device_takeovers_total", "Playback device takeovers"
)
COUNTED_PLAYS = Counter(
    "yukinoise_playback_counted_total", "Playback attempts reaching the threshold"
)
REDIS_MUTATION_SECONDS = Histogram(
    "yukinoise_playback_redis_mutation_seconds", "Redis playback CAS latency"
)

HEARTBEAT_TOLERANCE_MS = 2_000


def merge_intervals(
    intervals: Sequence[Sequence[int]], new_interval: tuple[int, int] | None = None
) -> list[list[int]]:
    normalized = [[min(int(a), int(b)), max(int(a), int(b))] for a, b in intervals]
    if new_interval is not None and new_interval[1] > new_interval[0]:
        normalized.append([new_interval[0], new_interval[1]])
    normalized.sort(key=lambda item: item[0])
    merged: list[list[int]] = []
    for start, end in normalized:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return merged


def covered_ms(intervals: Sequence[Sequence[int]]) -> int:
    return sum(max(0, int(end) - int(start)) for start, end in intervals)


@dataclass(slots=True)
class PlaybackService:
    uow: UnitOfWork
    repository: PlaybackRepository

    async def get_current(self, user_id: UUID) -> PlaybackStateResponse | None:
        state = await self.repository.get(user_id)
        return self._response(state) if state else None

    async def get_queue(self, user_id: UUID) -> PlaybackQueueResponse:
        state = await self._required(user_id)
        return PlaybackQueueResponse(
            current_index=state["current_index"],
            tracks=[self._track_response(track) for track in state["queue"]],
        )

    async def play(
        self,
        *,
        user_id: UUID,
        artist_id: UUID | None,
        device_id: UUID,
        context: PlaybackContext | None,
        offset_track_id: UUID | None,
        position_ms: int,
    ) -> PlaybackStateResponse:
        current = await self.repository.get(user_id)
        if context is None:
            if current is None:
                raise PlaybackNotFoundError
            position = self._position(current)
            current["active_device_id"] = str(device_id)
            current["is_playing"] = True
            current["anchor_position_ms"] = position
            current["anchor_time_ms"] = self._now_ms()
            current["last_heartbeat_ms"] = current["anchor_time_ms"]
            current["revision"] += 1
            await self._save(user_id, current["revision"] - 1, current)
            return self._response(current)

        queue = await self._build_queue(context, artist_id)
        if not queue:
            raise PlaybackContextNotFoundError
        index = 0
        if offset_track_id is not None:
            try:
                index = next(
                    i for i, track in enumerate(queue) if track.id == offset_track_id
                )
            except StopIteration as exc:
                raise PlaybackContextNotFoundError from exc
        track = queue[index]
        now = self._now_ms()
        state: dict[str, Any] = {
            "session_id": str(uuid4()),
            "revision": (current["revision"] + 1) if current else 1,
            "active_device_id": str(device_id),
            "context": {"type": context.type.value, "id": str(context.id)},
            "queue": [self._serialize_track(item) for item in queue],
            "current_index": index,
            "repeat_mode": RepeatMode.OFF.value,
            "attempt_id": str(uuid4()),
            "anchor_position_ms": min(position_ms, track.duration_seconds * 1000),
            "anchor_time_ms": now,
            "last_heartbeat_ms": now,
            "last_sequence": 0,
            "intervals": [],
            "count_status": "uncounted",
            "is_playing": True,
        }
        await self._save(user_id, current["revision"] if current else -1, state)
        return self._response(state)

    async def transfer(self, user_id: UUID, device_id: UUID) -> PlaybackStateResponse:
        state = await self._required(user_id)
        if state["active_device_id"] != str(device_id):
            DEVICE_TAKEOVERS.inc()
            position = self._position(state)
            state["active_device_id"] = str(device_id)
            state["is_playing"] = False
            state["anchor_position_ms"] = position
            state["anchor_time_ms"] = self._now_ms()
            await self._bump_and_save(user_id, state)
        return self._response(state)

    async def pause(self, user_id: UUID, device_id: UUID) -> PlaybackStateResponse:
        state = await self._controlled(user_id, device_id)
        state["anchor_position_ms"] = self._position(state)
        state["anchor_time_ms"] = self._now_ms()
        state["is_playing"] = False
        await self._bump_and_save(user_id, state)
        return self._response(state)

    async def seek(
        self, user_id: UUID, device_id: UUID, position_ms: int
    ) -> PlaybackStateResponse:
        state = await self._controlled(user_id, device_id)
        duration = self._current_track(state)["duration_ms"]
        state["anchor_position_ms"] = max(0, min(position_ms, duration))
        state["anchor_time_ms"] = self._now_ms()
        state["last_heartbeat_ms"] = state["anchor_time_ms"]
        await self._bump_and_save(user_id, state)
        return self._response(state)

    async def set_repeat(
        self, user_id: UUID, device_id: UUID, mode: RepeatMode
    ) -> PlaybackStateResponse:
        state = await self._controlled(user_id, device_id)
        state["repeat_mode"] = mode.value
        await self._bump_and_save(user_id, state)
        return self._response(state)

    async def next(
        self, user_id: UUID, device_id: UUID, *, ended: bool = False
    ) -> PlaybackStateResponse:
        state = await self._controlled(user_id, device_id)
        repeat = RepeatMode(state["repeat_mode"])
        index = state["current_index"]
        if ended and repeat == RepeatMode.TRACK:
            next_index = index
        elif index + 1 < len(state["queue"]):
            next_index = index + 1
        elif repeat == RepeatMode.CONTEXT:
            next_index = 0
        else:
            state["is_playing"] = False
            state["anchor_position_ms"] = self._current_track(state)["duration_ms"]
            await self._bump_and_save(user_id, state)
            return self._response(state)
        self._start_attempt(state, next_index)
        await self._bump_and_save(user_id, state)
        return self._response(state)

    async def previous(self, user_id: UUID, device_id: UUID) -> PlaybackStateResponse:
        state = await self._controlled(user_id, device_id)
        if self._position(state) > 3_000 or state["current_index"] == 0:
            next_index = state["current_index"]
        else:
            next_index = state["current_index"] - 1
        self._start_attempt(state, next_index)
        await self._bump_and_save(user_id, state)
        return self._response(state)

    async def progress(
        self,
        *,
        user_id: UUID,
        device_id: UUID,
        session_id: UUID,
        attempt_id: UUID,
        sequence: int,
        position_ms: int,
    ) -> PlaybackStateResponse:
        try:
            state = await self._controlled(user_id, device_id)
            now = self._now_ms()
            duration = self._current_track(state)["duration_ms"]
            if (
                state["session_id"] != str(session_id)
                or state["attempt_id"] != str(attempt_id)
                or sequence <= state["last_sequence"]
                or not state["is_playing"]
                or position_ms > duration
            ):
                raise PlaybackProgressRejectedError
            elapsed = max(0, now - state["last_heartbeat_ms"])
            start = int(state["anchor_position_ms"])
            forward = position_ms - start
            if forward < 0 or forward > elapsed + HEARTBEAT_TOLERANCE_MS:
                raise PlaybackProgressRejectedError
        except (PlaybackDeviceConflictError, PlaybackProgressRejectedError):
            REJECTED_PROGRESS.inc()
            raise

        state["intervals"] = merge_intervals(state["intervals"], (start, position_ms))
        state["anchor_position_ms"] = position_ms
        state["anchor_time_ms"] = now
        state["last_heartbeat_ms"] = now
        state["last_sequence"] = sequence
        listened = covered_ms(state["intervals"])
        should_count = state["count_status"] == "uncounted" and listened >= math.ceil(
            duration / 2
        )
        if should_count:
            state["count_status"] = "count_pending"
        await self._bump_and_save(user_id, state)
        if should_count:
            track_id = UUID(self._current_track(state)["id"])
            count_committed = False
            try:
                updated = await self.uow.tracks.increment_play_count(track_id)
                if updated:
                    await self.uow.commit()
                    count_committed = True
                    COUNTED_PLAYS.inc()
                    latest = await self._required(user_id)
                    if latest["attempt_id"] == str(attempt_id):
                        latest["count_status"] = "counted"
                        await self._bump_and_save(user_id, latest)
                        state = latest
                else:
                    latest = await self._required(user_id)
                    if latest["attempt_id"] == str(attempt_id):
                        latest["count_status"] = "uncounted"
                        await self._bump_and_save(user_id, latest)
            except Exception:
                if not count_committed:
                    rollback_state = await self.repository.get(user_id)
                    if rollback_state and rollback_state["attempt_id"] == str(
                        attempt_id
                    ):
                        rollback_state["count_status"] = "uncounted"
                        await self._bump_and_save(user_id, rollback_state)
                raise
        return self._response(state)

    async def stop(self, user_id: UUID, device_id: UUID) -> None:
        await self._controlled(user_id, device_id)
        await self.repository.delete(user_id)

    async def _build_queue(
        self, context: PlaybackContext, artist_id: UUID | None
    ) -> Sequence[Track]:
        if context.type == PlaybackContextType.TRACK:
            track = await self.uow.tracks.get_track_by_id(context.id)
            return [track] if track else []
        if context.type == PlaybackContextType.RELEASE:
            return await self.uow.tracks.get_public_tracks_for_release(context.id)
        return await self.uow.playlists.get_accessible_playlist_tracks_for_playback(
            context.id, artist_id
        )

    async def _required(self, user_id: UUID) -> dict[str, Any]:
        state = await self.repository.get(user_id)
        if state is None:
            raise PlaybackNotFoundError
        return state

    async def _controlled(self, user_id: UUID, device_id: UUID) -> dict[str, Any]:
        state = await self._required(user_id)
        if state["active_device_id"] != str(device_id):
            raise PlaybackDeviceConflictError
        return state

    async def _bump_and_save(self, user_id: UUID, state: dict[str, Any]) -> None:
        previous = state["revision"]
        state["revision"] = previous + 1
        await self._save(user_id, previous, state)

    async def _save(
        self, user_id: UUID, expected_revision: int, state: dict[str, Any]
    ) -> None:
        with REDIS_MUTATION_SECONDS.time():
            saved = await self.repository.compare_and_set(
                user_id, expected_revision, state
            )
        if not saved:
            raise PlaybackConflictError

    def _start_attempt(self, state: dict[str, Any], index: int) -> None:
        now = self._now_ms()
        state.update(
            current_index=index,
            attempt_id=str(uuid4()),
            anchor_position_ms=0,
            anchor_time_ms=now,
            last_heartbeat_ms=now,
            last_sequence=0,
            intervals=[],
            count_status="uncounted",
            is_playing=True,
        )

    def _position(self, state: dict[str, Any]) -> int:
        position = int(state["anchor_position_ms"])
        if state["is_playing"]:
            position += max(0, self._now_ms() - int(state["anchor_time_ms"]))
        return min(position, int(self._current_track(state)["duration_ms"]))

    @staticmethod
    def _current_track(state: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], state["queue"][state["current_index"]])

    def _response(self, state: dict[str, Any]) -> PlaybackStateResponse:
        return PlaybackStateResponse(
            session_id=UUID(state["session_id"]),
            revision=state["revision"],
            active_device_id=UUID(state["active_device_id"]),
            context=PlaybackContext.model_validate(state["context"]),
            current_track=self._track_response(self._current_track(state)),
            current_index=state["current_index"],
            queue_length=len(state["queue"]),
            attempt_id=UUID(state["attempt_id"]),
            heartbeat_sequence=state["last_sequence"],
            position_ms=self._position(state),
            is_playing=state["is_playing"],
            repeat_mode=RepeatMode(state["repeat_mode"]),
            listened_ms=covered_ms(state["intervals"]),
            counted=state["count_status"] == "counted",
        )

    @staticmethod
    def _serialize_track(track: Track) -> dict[str, Any]:
        return {
            "id": str(track.id),
            "title": track.title,
            "duration_ms": track.duration_seconds * 1000,
        }

    @staticmethod
    def _track_response(track: dict[str, Any]) -> PlaybackTrack:
        track_id = UUID(track["id"])
        return PlaybackTrack(
            id=track_id,
            title=track["title"],
            duration_ms=track["duration_ms"],
            stream_url=f"/tracks/{track_id}/stream",
        )

    @staticmethod
    def _now_ms() -> int:
        return time.time_ns() // 1_000_000
