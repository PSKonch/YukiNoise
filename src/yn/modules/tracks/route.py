from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.tracks.deps import get_track_service
from yn.modules.tracks.errors import EmptyTrackUpdateError
from yn.modules.tracks.schemas import TrackRead, TrackUpdate, TrackUploadAccepted
from yn.modules.tracks.service import TrackService
from yn.modules.users.auth import get_current_user
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/tracks", tags=["tracks"])


# Public read
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


# Owner read
@router.get("/me")
async def get_owned_tracks(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    track_service: Annotated[TrackService, Depends(get_track_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[TrackRead]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    tracks = await track_service.get_owned_tracks_by_artist_id(
        artist_id=current_user.artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [TrackRead.model_validate(track, from_attributes=True) for track in tracks]


@router.get("/me/{track_id}")
async def get_owned_track_by_id(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    track_service: Annotated[TrackService, Depends(get_track_service)],
    track_id: UUID,
) -> TrackRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    track = await track_service.get_owned_track_by_id(
        track_id=track_id,
        artist_id=current_user.artist_id,
    )
    return TrackRead.model_validate(track, from_attributes=True)


# Owner write
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
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    track = await track_service.upload_track(
        release_id=release_id,
        current_artist_id=current_user.artist_id,
        title=title,
        track_number_in_release=track_number_in_release,
        genres=genres or [],
        file=file,
    )
    return TrackUploadAccepted.model_validate(track, from_attributes=True)


@router.patch("/{track_id}")
async def update_track(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    track_service: Annotated[TrackService, Depends(get_track_service)],
    track_id: UUID,
    payload: TrackUpdate,
) -> TrackRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    if (
        payload.title is None
        and payload.track_number_in_release is None
        and payload.genres is None
    ):
        raise EmptyTrackUpdateError

    track = await track_service.update_track(
        track_id=track_id,
        artist_id=current_user.artist_id,
        title=payload.title,
        track_number_in_release=payload.track_number_in_release,
        genres=payload.genres,
    )
    return TrackRead.model_validate(track, from_attributes=True)


@router.delete("/{track_id}")
async def delete_track(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    track_service: Annotated[TrackService, Depends(get_track_service)],
    track_id: UUID,
) -> dict[str, str]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    await track_service.delete_track(
        track_id=track_id,
        artist_id=current_user.artist_id,
    )

    return {"detail": "Track deleted successfully"}
