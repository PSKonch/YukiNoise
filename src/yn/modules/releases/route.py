from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.auth.auth import get_current_user
from yn.modules.releases.cover_uploader import (
    ReleaseCoverUploadPayload,
    build_release_cover_storage_key,
    copy_upload_to_shared_tempfile,
)
from yn.modules.releases.deps import get_release_read_service, get_release_service
from yn.modules.releases.errors import ReleaseCoverUploadFailedError
from yn.modules.releases.schemas import (
    ReleaseCoverUploadAccepted,
    ReleaseCreate,
    ReleaseRead,
    ReleaseSchedule,
    ReleaseWithTracksAndAuthorRead,
)
from yn.modules.releases.service import ReleaseService
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params
from yn.tasks.release_cover_upload import process_release_cover_upload

router = APIRouter(prefix="/releases", tags=["releases"])


# Public read
@router.get("/")
async def get_releases(
    release_service: Annotated[ReleaseService, Depends(get_release_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ReleaseRead]:
    releases = await release_service.get_releases(
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ReleaseRead.model_validate(release, from_attributes=True)
        for release in releases
    ]


@router.get("/search")
async def search_releases(
    search_term: str,
    release_service: Annotated[ReleaseService, Depends(get_release_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ReleaseRead]:
    releases = await release_service.trgm_search_by_title(
        search_term,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ReleaseRead.model_validate(release, from_attributes=True)
        for release in releases
    ]


@router.get("/with-tracks-and-author")
async def get_releases_with_tracks_and_author_profile(
    release_service: Annotated[ReleaseService, Depends(get_release_read_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ReleaseWithTracksAndAuthorRead]:
    releases = await release_service.get_releases_with_tracks_and_author_profile(
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ReleaseWithTracksAndAuthorRead.model_validate(release, from_attributes=True)
        for release in releases
    ]


@router.get("/{release_id:uuid}")
async def get_release_by_id(
    release_service: Annotated[ReleaseService, Depends(get_release_read_service)],
    release_id: UUID,
) -> ReleaseRead:
    release = await release_service.get_release_by_id(release_id)
    return ReleaseRead.model_validate(release, from_attributes=True)


@router.get("/{release_id:uuid}/with-tracks-and-author")
async def get_release_with_tracks_and_author_profile_by_id(
    release_service: Annotated[ReleaseService, Depends(get_release_read_service)],
    release_id: UUID,
) -> ReleaseWithTracksAndAuthorRead:
    release = await release_service.get_release_with_tracks_and_author_profile_by_id(
        release_id=release_id
    )
    return ReleaseWithTracksAndAuthorRead.model_validate(release, from_attributes=True)


# Owner read
@router.get("/me")
async def get_owned_releases(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    release_service: Annotated[ReleaseService, Depends(get_release_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ReleaseRead]:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    releases = await release_service.get_owned_releases(
        artist_id=current_user.artist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ReleaseRead.model_validate(release, from_attributes=True)
        for release in releases
    ]


@router.get("/me/{release_id:uuid}")
async def get_owned_release_by_id(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    release_service: Annotated[ReleaseService, Depends(get_release_service)],
    release_id: UUID,
) -> ReleaseRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    release = await release_service.get_owned_release_by_id_including_deleted(
        release_id=release_id,
        artist_id=current_user.artist_id,
    )
    return ReleaseRead.model_validate(release, from_attributes=True)


# Owner write
@router.post("/")
async def create_release(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    release_service: Annotated[ReleaseService, Depends(get_release_service)],
    payload: ReleaseCreate,
) -> ReleaseRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    release = await release_service.create_release(
        artist_id=current_user.artist_id,
        title=payload.title,
        description=payload.description,
        cover_path=payload.cover_path,
        release_type=payload.release_type,
    )
    return ReleaseRead.model_validate(release, from_attributes=True)


@router.patch("/{release_id:uuid}/description")
async def update_release_description(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    release_service: Annotated[ReleaseService, Depends(get_release_service)],
    release_id: UUID,
    description: str,
) -> ReleaseRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    release = await release_service.update_description_of_release(
        artist_id=current_user.artist_id,
        release_id=release_id,
        description=description,
    )
    return ReleaseRead.model_validate(release, from_attributes=True)


@router.patch("/{release_id:uuid}/cover")
async def upload_release_cover(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    release_service: Annotated[ReleaseService, Depends(get_release_service)],
    release_id: UUID,
    cover: Annotated[UploadFile, File(...)],
) -> ReleaseCoverUploadAccepted:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    await release_service.get_owned_release_by_id(
        release_id=release_id,
        artist_id=current_user.artist_id,
    )

    temp_path = await copy_upload_to_shared_tempfile(cover)
    cover_path = build_release_cover_storage_key(
        release_id=release_id,
        filename=cover.filename,
    )

    try:
        await process_release_cover_upload.kiq(
            payload=ReleaseCoverUploadPayload(
                release_id=release_id,
                artist_id=current_user.artist_id,
                cover_path=cover_path,
                temp_path=temp_path,
            ).to_message()
        )
    except Exception as exc:
        from pathlib import Path

        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise ReleaseCoverUploadFailedError from exc

    return ReleaseCoverUploadAccepted(release_id=release_id)


@router.patch("/{release_id:uuid}/release")
async def schedule_release(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    release_service: Annotated[ReleaseService, Depends(get_release_service)],
    release_id: UUID,
    payload: ReleaseSchedule,
) -> ReleaseRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    release = await release_service.schedule_release(
        release_id=release_id,
        artist_id=current_user.artist_id,
        release_date=payload.release_date,
    )
    return ReleaseRead.model_validate(release, from_attributes=True)


@router.delete("/{release_id:uuid}/release")
async def cancel_release(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    release_service: Annotated[ReleaseService, Depends(get_release_service)],
    release_id: UUID,
) -> ReleaseRead:
    if current_user.artist_id is None:
        raise ArtistNotFoundError

    release = await release_service.unschedule_release(
        release_id=release_id,
        artist_id=current_user.artist_id,
    )
    return ReleaseRead.model_validate(release, from_attributes=True)
