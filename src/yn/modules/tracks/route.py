from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile

from yn.modules.profiles.errors import ProfileNotFoundError
from yn.modules.tracks.deps import get_track_service
from yn.modules.tracks.schemas import TrackRead, TrackUploadAccepted
from yn.modules.tracks.service import TrackService
from yn.modules.users.auth import get_current_user
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.post("/")
async def upload_track(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    track_service: Annotated[TrackService, Depends(get_track_service)],
    release_id: Annotated[UUID, Form(...)],
    title: Annotated[str, Form(...)],
    track_number_in_release: Annotated[int, Form(...)],
    file: Annotated[UploadFile, File(...)],
    genres: Annotated[list[str] | None, Form()] = None,
) -> TrackUploadAccepted:
    if current_user.profile_id is None:
        raise ProfileNotFoundError

    track = await track_service.upload_track(
        release_id=release_id,
        current_profile_id=current_user.profile_id,
        title=title,
        track_number_in_release=track_number_in_release,
        genres=genres or [],
        file=file,
    )
    return TrackUploadAccepted.model_validate(track, from_attributes=True)


@router.get("/")
async def get_tracks(
    track_service: Annotated[TrackService, Depends(get_track_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[TrackRead]:
    tracks = await track_service.get_tracks(
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [TrackRead.model_validate(track, from_attributes=True) for track in tracks]


@router.get("/{track_id}")
async def get_track_by_id(
    track_service: Annotated[TrackService, Depends(get_track_service)],
    track_id: UUID,
) -> TrackRead:
    track = await track_service.get_track_by_id(track_id)
    return TrackRead.model_validate(track, from_attributes=True)
