from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import StreamingResponse

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.auth.auth import get_current_user
from yn.modules.tracks.deps import get_track_read_service, get_track_service
from yn.modules.tracks.errors import EmptyTrackUpdateError
from yn.modules.tracks.schemas import TrackRead, TrackUpdate, TrackUploadAccepted
from yn.modules.tracks.service import TrackService
from yn.modules.users.dto import UserDTO
from yn.shared.minio import get_minio_storage
from yn.shared.pagination import PaginationParams, get_pagination_params
from yn.shared.settings import settings

router = APIRouter(prefix="/tracks", tags=["tracks"])


def parse_byte_range(value: str | None, file_size: int) -> tuple[int, int, int]:
    """Return (status, start, end) for a single RFC 7233 byte range."""
    if file_size <= 0:
        raise ValueError("empty object")
    if value is None:
        return 200, 0, file_size - 1
    unit, requested = value.strip().split("=", 1)
    if unit.lower() != "bytes" or "," in requested:
        raise ValueError("only one byte range is supported")
    first, last = requested.split("-", 1)
    if first:
        start = int(first)
        end = int(last) if last else file_size - 1
    else:
        suffix = int(last)
        if suffix <= 0:
            raise ValueError("invalid suffix")
        start = max(0, file_size - suffix)
        end = file_size - 1
    if start < 0 or start >= file_size or end < start:
        raise ValueError("unsatisfiable range")
    return 206, start, min(end, file_size - 1)


# Public read
@router.get("/")
async def get_tracks(
    track_service: Annotated[TrackService, Depends(get_track_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[TrackRead]:
    tracks = await track_service.get_tracks(
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [TrackRead.model_validate(track, from_attributes=True) for track in tracks]


@router.get("/{track_id:uuid}")
async def get_track_by_id(
    track_service: Annotated[TrackService, Depends(get_track_read_service)],
    track_id: UUID,
) -> TrackRead:
    track = await track_service.get_track_by_id(track_id)
    return TrackRead.model_validate(track, from_attributes=True)


@router.get("/{track_id:uuid}/stream")
async def stream_track_by_id(
    track_service: Annotated[TrackService, Depends(get_track_read_service)],
    track_id: UUID,
    request: Request,
) -> Response:
    track = await track_service.get_track_by_id(track_id)
    storage = get_minio_storage()
    stat = await storage.stat(settings.minio_bucket, track.path)
    file_size = stat.size
    range_header = request.headers.get("range")
    try:
        status_code, start, end = parse_byte_range(range_header, file_size)
    except (TypeError, ValueError):
        return Response(
            status_code=416,
            headers={
                "Content-Range": f"bytes */{file_size}",
                "Accept-Ranges": "bytes",
            },
        )

    length = end - start + 1

    async def content() -> "AsyncIterator[bytes]":
        async for chunk in storage.iter_object_range(
            settings.minio_bucket, track.path, offset=start, length=length
        ):
            yield chunk

    media_type = track.mime_type or "audio/mpeg"
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Disposition": f'inline; filename="{track.path}"',
    }
    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    return StreamingResponse(
        content(),
        status_code=status_code,
        media_type=media_type,
        headers=headers,
    )


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


@router.get("/me/{track_id:uuid}")
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


@router.patch("/{track_id:uuid}")
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


@router.delete("/{track_id:uuid}")
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
