import time
from dataclasses import dataclass
from uuid import UUID, uuid4

from yn.modules.playback.errors import PlaybackNotFoundError, TrackNotFoundError
from yn.modules.playback.repository import PlaybackRepository
from yn.modules.playback.schemas import PlaybackSessionResponse
from yn.shared.unit_of_work import UnitOfWork


@dataclass(slots=True)
class PlaybackState:
    session_id: UUID
    track_id: UUID
    position: int
    duration: int
    updated_at: int
    is_paused: int

    @classmethod
    def from_mapping(cls, mapping: dict[str, str]) -> "PlaybackState":
        try:
            return cls(
                session_id=UUID(mapping["session_id"]),
                track_id=UUID(mapping["track_id"]),
                position=int(mapping["position"]),
                duration=int(mapping["duration"]),
                updated_at=int(mapping["updated_at"]),
                is_paused=int(mapping["is_paused"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise PlaybackNotFoundError from exc

    def to_mapping(self) -> dict[str, int | str]:
        return {
            "session_id": str(self.session_id),
            "track_id": str(self.track_id),
            "position": self.position,
            "duration": self.duration,
            "updated_at": self.updated_at,
            "is_paused": self.is_paused,
        }


class PlaybackService:
    def __init__(self, uow: UnitOfWork, playback_repository: PlaybackRepository):
        self.uow = uow
        self.playback_repository = playback_repository

    async def start_playback(
        self, track_id: UUID, user_id: UUID
    ) -> PlaybackSessionResponse:
        track = await self.uow.tracks.get_track_by_id(track_id)
        if track is None:
            raise TrackNotFoundError

        session_id = uuid4()
        now = self._now()
        state = PlaybackState(
            session_id=session_id,
            track_id=track_id,
            position=0,
            duration=track.duration_seconds,
            updated_at=now,
            is_paused=0,
        )

        await self.playback_repository.delete_playback(user_id)
        await self.playback_repository.save_playback(
            user_id,
            session_id=state.session_id,
            track_id=state.track_id,
            position=state.position,
            duration=state.duration,
            updated_at=state.updated_at,
            is_paused=state.is_paused,
        )
        return self._to_response(state, position=state.position)

    async def stop_playback(self, user_id: UUID) -> None:
        await self._get_playback_state(user_id)
        await self.playback_repository.delete_playback(user_id)

    async def pause_playback(self, user_id: UUID) -> PlaybackSessionResponse:
        state = await self._get_playback_state(user_id)
        now = self._now()
        current_position = self._current_position(state, now)
        state.position = current_position
        state.updated_at = now
        state.is_paused = 1

        await self.playback_repository.save_playback(
            user_id,
            session_id=state.session_id,
            track_id=state.track_id,
            position=state.position,
            duration=state.duration,
            updated_at=state.updated_at,
            is_paused=state.is_paused,
        )
        return self._to_response(state, position=current_position)

    async def resume_playback(self, user_id: UUID) -> PlaybackSessionResponse:
        state = await self._get_playback_state(user_id)
        now = self._now()
        state.updated_at = now
        state.is_paused = 0

        await self.playback_repository.save_playback(
            user_id,
            session_id=state.session_id,
            track_id=state.track_id,
            position=state.position,
            duration=state.duration,
            updated_at=state.updated_at,
            is_paused=state.is_paused,
        )
        return self._to_response(state, position=self._current_position(state, now))

    async def change_playback_position(
        self, user_id: UUID, position: int
    ) -> PlaybackSessionResponse:
        state = await self._get_playback_state(user_id)
        now = self._now()
        state.position = self._clamp_position(position, state.duration)
        state.updated_at = now

        await self.playback_repository.save_playback(
            user_id,
            session_id=state.session_id,
            track_id=state.track_id,
            position=state.position,
            duration=state.duration,
            updated_at=state.updated_at,
            is_paused=state.is_paused,
        )
        return self._to_response(state, position=state.position)

    async def get_current_playback(
        self, user_id: UUID
    ) -> PlaybackSessionResponse | None:
        playback = await self.playback_repository.get_playback(user_id)
        if playback is None:
            return None

        state = PlaybackState.from_mapping(playback)
        current_position = self._current_position(state, self._now())
        return self._to_response(state, position=current_position)

    async def _get_playback_state(self, user_id: UUID) -> PlaybackState:
        playback = await self.playback_repository.get_playback(user_id)
        if playback is None:
            raise PlaybackNotFoundError
        return PlaybackState.from_mapping(playback)

    @staticmethod
    def _clamp_position(position: int, duration: int) -> int:
        return max(0, min(position, duration))

    def _current_position(self, state: PlaybackState, now: int) -> int:
        if state.is_paused:
            return self._clamp_position(state.position, state.duration)

        elapsed = max(now - state.updated_at, 0)
        return self._clamp_position(state.position + elapsed, state.duration)

    def _to_response(
        self, state: PlaybackState, *, position: int
    ) -> PlaybackSessionResponse:
        return PlaybackSessionResponse(
            session_id=state.session_id,
            track_id=state.track_id,
            position=position,
            duration=state.duration,
            is_paused=bool(state.is_paused),
        )

    @staticmethod
    def _now() -> int:
        return int(time.time())
