from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from yn.modules.albums.cover_uploader import (
    AlbumPictureUploadPayload,
    build_album_picture_storage_key,
    copy_upload_to_shared_tempfile,
)
from yn.modules.albums.deps import get_album_service
from yn.modules.albums.errors import AlbumPictureUploadFailedError
from yn.modules.albums.schemas import (
    AlbumCreate,
    AlbumPictureUploadAccepted,
    AlbumRead,
    AlbumWithTracksAndAuthorRead,
)
from yn.modules.albums.service import AlbumService
from yn.modules.profiles.errors import ProfileNotFoundError
from yn.modules.users.auth import get_current_user
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params
from yn.tasks.album_picture_upload import process_album_picture_upload

router = APIRouter(prefix="/albums", tags=["albums"])


@router.post("/")
async def create_album(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    album_service: Annotated[AlbumService, Depends(get_album_service)],
    payload: AlbumCreate,
) -> AlbumRead:
    if current_user.profile_id is None:
        raise ProfileNotFoundError

    album = await album_service.create_album(
        profile_id=current_user.profile_id,
        title=payload.title,
        description=payload.description,
        picture_path=payload.picture_path,
    )
    return AlbumRead.model_validate(album, from_attributes=True)


@router.patch("/{album_id}/picture")
async def upload_album_picture(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    album_service: Annotated[AlbumService, Depends(get_album_service)],
    album_id: UUID,
    picture: Annotated[UploadFile, File(...)],
) -> AlbumPictureUploadAccepted:
    if current_user.profile_id is None:
        raise ProfileNotFoundError

    await album_service.get_owned_album_by_id(
        album_id=album_id,
        profile_id=current_user.profile_id,
    )

    temp_path = await copy_upload_to_shared_tempfile(picture)
    picture_path = build_album_picture_storage_key(
        album_id=album_id,
        filename=picture.filename,
    )

    try:
        await process_album_picture_upload.kiq(
            payload=AlbumPictureUploadPayload(
                album_id=album_id,
                profile_id=current_user.profile_id,
                picture_path=picture_path,
                temp_path=temp_path,
            ).to_message()
        )
    except Exception as exc:
        from pathlib import Path

        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise AlbumPictureUploadFailedError from exc

    return AlbumPictureUploadAccepted(album_id=album_id)


@router.get("/")
async def get_albums(
    album_service: Annotated[AlbumService, Depends(get_album_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[AlbumRead]:
    albums = await album_service.get_albums(
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [AlbumRead.model_validate(album, from_attributes=True) for album in albums]


@router.get("/search")
async def search_albums(
    search_term: str,
    album_service: Annotated[AlbumService, Depends(get_album_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[AlbumRead]:
    albums = await album_service.trgm_search_by_title(
        search_term,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [AlbumRead.model_validate(album, from_attributes=True) for album in albums]


@router.get("/with-tracks-and-author")
async def get_albums_with_tracks_and_author_profile(
    album_service: Annotated[AlbumService, Depends(get_album_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[AlbumWithTracksAndAuthorRead]:
    albums = await album_service.get_albums_with_tracks_and_author_profile(
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        AlbumWithTracksAndAuthorRead.model_validate(album, from_attributes=True)
        for album in albums
    ]
