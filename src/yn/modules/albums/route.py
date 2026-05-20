from typing import Annotated

from fastapi import APIRouter, Depends

from yn.modules.albums.deps import get_album_service
from yn.modules.albums.schemas import (
    AlbumCreate,
    AlbumRead,
    AlbumWithTracksAndAuthorRead,
)
from yn.modules.albums.service import AlbumService
from yn.modules.profiles.errors import ProfileNotFoundError
from yn.modules.users.auth import get_current_user
from yn.modules.users.dto import UserDTO

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


@router.get("/")
async def get_albums(
    album_service: Annotated[AlbumService, Depends(get_album_service)],
) -> list[AlbumRead]:
    albums = await album_service.get_albums()
    return [AlbumRead.model_validate(album, from_attributes=True) for album in albums]


@router.get("/search")
async def search_albums(
    search_term: str,
    album_service: Annotated[AlbumService, Depends(get_album_service)],
) -> list[AlbumRead]:
    albums = await album_service.trgm_search_by_title(search_term)
    return [AlbumRead.model_validate(album, from_attributes=True) for album in albums]


@router.get("/with-tracks-and-author")
async def get_albums_with_tracks_and_author_profile(
    album_service: Annotated[AlbumService, Depends(get_album_service)],
) -> list[AlbumWithTracksAndAuthorRead]:
    albums = await album_service.get_albums_with_tracks_and_author_profile()
    return [
        AlbumWithTracksAndAuthorRead.model_validate(album, from_attributes=True)
        for album in albums
    ]
