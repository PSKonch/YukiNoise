from typing import Annotated

from fastapi import APIRouter, Depends

from yn.modules.profiles.deps import get_profile_service
from yn.modules.profiles.errors import (
    EmptyProfileUpdateError,
    ProfileNotFoundError,
)
from yn.modules.profiles.schemas import ProfileCreate, ProfileRead, ProfileUpdate
from yn.modules.profiles.service import ProfileService
from yn.modules.users.auth import get_current_user
from yn.modules.users.dto import UserDTO
from yn.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me")
async def read_current_user_profile(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileRead:
    profile = await profile_service.get_profile_by_user_id(current_user.id)
    return ProfileRead.model_validate(profile, from_attributes=True)


@router.put("/me")
async def update_current_user_profile(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    payload: ProfileUpdate,
) -> dict[str, str]:
    if (
        payload.displayed_name is None
        and payload.bio is None
        and payload.social_links is None
    ):
        raise EmptyProfileUpdateError

    profile_exists = await profile_service.update_profile(
        user_id=current_user.id,
        displayed_name=payload.displayed_name,
        bio=payload.bio,
        social_links=payload.social_links,
    )

    if not profile_exists:
        raise ProfileNotFoundError

    return {"detail": "Profile updated successfully"}


@router.delete("/me")
async def delete_current_user_profile(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> dict[str, str]:
    profile_exists = await profile_service.hard_delete_profile(user_id=current_user.id)

    if not profile_exists:
        raise ProfileNotFoundError

    return {"detail": "Profile deleted successfully"}


@router.post("/")
async def create_profile(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    payload: ProfileCreate,
) -> dict[str, str]:
    await profile_service.create_profile(
        user_id=current_user.id,
        displayed_name=payload.displayed_name,
        bio=payload.bio,
        social_links=payload.social_links,
    )
    return {"detail": "Profile created successfully"}


@router.get("/search")
async def search_profiles(
    query: str,
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ProfileRead]:
    profiles = await profile_service.full_text_search_profiles(
        query,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ProfileRead.model_validate(profile, from_attributes=True)
        for profile in profiles
    ]


@router.get("/")
async def get_all_profiles(
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> list[ProfileRead]:
    profiles = await profile_service.get_all_profiles(
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [
        ProfileRead.model_validate(profile, from_attributes=True)
        for profile in profiles
    ]
