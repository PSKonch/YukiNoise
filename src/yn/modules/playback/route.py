from typing import Annotated

from fastapi import APIRouter, Depends

from yn.modules.auth.auth import get_current_user
from yn.modules.playback.deps import get_playback_service
from yn.modules.playback.schemas import (
    PlaybackSeekRequest,
    PlaybackSessionResponse,
    PlaybackStartRequest,
)
from yn.modules.playback.service import PlaybackService
from yn.modules.users.dto import UserDTO

router = APIRouter(prefix="/playback", tags=["playback"])


@router.post("/start")
async def start_playback(
    payload: PlaybackStartRequest,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playback_service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackSessionResponse:
    return await playback_service.start_playback(
        track_id=payload.track_id,
        user_id=current_user.id,
    )


@router.post("/pause")
async def pause_playback(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playback_service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackSessionResponse:
    return await playback_service.pause_playback(user_id=current_user.id)


@router.post("/resume")
async def resume_playback(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playback_service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackSessionResponse:
    return await playback_service.resume_playback(user_id=current_user.id)


@router.post("/stop")
async def stop_playback(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playback_service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> dict[str, str]:
    await playback_service.stop_playback(user_id=current_user.id)
    return {"detail": "Playback stopped successfully"}


@router.post("/change_position")
async def change_playback_position(
    payload: PlaybackSeekRequest,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playback_service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackSessionResponse:
    return await playback_service.change_playback_position(
        user_id=current_user.id,
        position=payload.position,
    )


@router.get("/current")
async def get_current_playback(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    playback_service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackSessionResponse | None:
    return await playback_service.get_current_playback(user_id=current_user.id)
