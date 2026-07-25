import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Response, WebSocket, WebSocketDisconnect, status
from prometheus_client import Gauge

from yn.modules.auth.auth import get_current_user
from yn.modules.auth.deps import get_security_manager
from yn.modules.auth.security import SecurityManager
from yn.modules.auth.service import AuthService
from yn.modules.playback.deps import get_playback_repository, get_playback_service
from yn.modules.playback.repository import PlaybackRepository
from yn.modules.playback.schemas import (
    DeviceRequest,
    PlaybackNextRequest,
    PlaybackPlayRequest,
    PlaybackProgressRequest,
    PlaybackQueueResponse,
    PlaybackRepeatRequest,
    PlaybackSeekRequest,
    PlaybackStateResponse,
    WebSocketAuthMessage,
)
from yn.modules.playback.service import PlaybackService
from yn.modules.users.dto import UserDTO
from yn.shared.database import async_primary_session
from yn.shared.unit_of_work import UnitOfWork

router = APIRouter(prefix="/me/player", tags=["player"])
WEBSOCKET_CONNECTIONS = Gauge(
    "yukinoise_playback_websocket_connections", "Active playback WebSockets"
)


@router.get("")
async def current(
    user: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackStateResponse | None:
    return await service.get_current(user.id)


@router.get("/queue")
async def queue(
    user: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackQueueResponse:
    return await service.get_queue(user.id)


@router.put("/play")
async def play(
    payload: PlaybackPlayRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackStateResponse:
    return await service.play(
        user_id=user.id,
        artist_id=user.artist_id,
        device_id=payload.device_id,
        context=payload.context,
        offset_track_id=payload.offset_track_id,
        position_ms=payload.position_ms,
    )


@router.put("/transfer")
async def transfer(
    payload: DeviceRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackStateResponse:
    return await service.transfer(user.id, payload.device_id)


@router.put("/pause")
async def pause(
    payload: DeviceRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackStateResponse:
    return await service.pause(user.id, payload.device_id)


@router.put("/seek")
async def seek(
    payload: PlaybackSeekRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackStateResponse:
    return await service.seek(user.id, payload.device_id, payload.position_ms)


@router.put("/repeat")
async def repeat(
    payload: PlaybackRepeatRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackStateResponse:
    return await service.set_repeat(user.id, payload.device_id, payload.mode)


@router.post("/next")
async def next_track(
    payload: PlaybackNextRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackStateResponse:
    return await service.next(user.id, payload.device_id, ended=payload.ended)


@router.post("/previous")
async def previous_track(
    payload: DeviceRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackStateResponse:
    return await service.previous(user.id, payload.device_id)


@router.post("/progress")
async def progress(
    payload: PlaybackProgressRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> PlaybackStateResponse:
    return await service.progress(
        user_id=user.id,
        device_id=payload.device_id,
        session_id=payload.session_id,
        attempt_id=payload.attempt_id,
        sequence=payload.sequence,
        position_ms=payload.position_ms,
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def stop(
    payload: DeviceRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PlaybackService, Depends(get_playback_service)],
) -> Response:
    await service.stop(user.id, payload.device_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.websocket("/events")
async def events(
    websocket: WebSocket,
    security: Annotated[SecurityManager, Depends(get_security_manager)],
    repository: Annotated[PlaybackRepository, Depends(get_playback_repository)],
) -> None:
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        auth = WebSocketAuthMessage.model_validate(raw)
        if auth.type != "authenticate":
            await websocket.close(code=4401)
            return
        async with async_primary_session() as session:
            async with UnitOfWork(session) as uow:
                auth_service = AuthService(uow=uow, security=security)
                user = await auth_service.get_user_from_access_token(auth.access_token)
    except Exception:
        await websocket.close(code=4401)
        return

    WEBSOCKET_CONNECTIONS.inc()
    try:
        state = await repository.get(user.id)
        await websocket.send_json(
            {
                "type": "playback_changed",
                "revision": state.get("revision") if state else None,
                "active_device_id": state.get("active_device_id") if state else None,
            }
        )
        async for message in repository.subscribe(user.id):
            state = json.loads(message)
            await websocket.send_json(
                {
                    "type": "playback_changed",
                    "revision": state.get("revision"),
                    "active_device_id": state.get("active_device_id"),
                }
            )
    except WebSocketDisconnect:
        pass
    finally:
        WEBSOCKET_CONNECTIONS.dec()
