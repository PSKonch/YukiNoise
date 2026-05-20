from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile

from yn.modules.profiles.errors import ProfileNotFoundError
from yn.modules.tracks.deps import get_track_service
from yn.modules.tracks.schemas import TrackRead
from yn.modules.tracks.service import TrackService
from yn.modules.users.auth import get_current_user
from yn.modules.users.dto import UserDTO

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.post("/")
async def upload_track(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    track_service: Annotated[TrackService, Depends(get_track_service)],
    album_id: Annotated[UUID, Form(...)],
    title: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    genres: Annotated[list[str] | None, Form()] = None,
) -> TrackRead:
    if current_user.profile_id is None:
        raise ProfileNotFoundError

    track = await track_service.upload_track(
        album_id=album_id,
        current_profile_id=current_user.profile_id,
        title=title,
        genres=genres or [],
        file=file,
    )
    return TrackRead.model_validate(track, from_attributes=True)
