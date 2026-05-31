from uuid import UUID

from yn.shared.unit_of_work import UnitOfWork


class PlaybackService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def start_playback(self, track_id: UUID, user_id: UUID) -> None: ...

    async def stop_playback(self, session_id: UUID, user_id: UUID) -> None: ...

    async def pause_playback(self, session_id: UUID, user_id: UUID) -> None: ...

    async def resume_playback(self, session_id: UUID, user_id: UUID) -> None: ...

    async def change_playback_position(
        self, session_id: UUID, position: int, user_id: UUID
    ) -> None: ...

    async def get_current_playback(self, user_id: UUID) -> None: ...
