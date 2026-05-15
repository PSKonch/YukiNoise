from typing import Annotated

from fastapi import APIRouter, Depends

from yn.modules.profiles.deps import get_profile_service
from yn.modules.profiles.dto import ProfileDTO
from yn.modules.profiles.schemas import ProfileCreate, ProfileRead, ProfileUpdate
from yn.modules.profiles.service import ProfileService
from yn.modules.users.auth import get_current_user
from yn.modules.users.dto import UserDTO

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=ProfileRead)
async def read_current_user_profile(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    profile = await profile_service.get_profile_by_user_id(current_user.id)
    return ProfileRead.model_validate(profile, from_attributes=True)


@router.put("/me")
async def update_current_user_profile(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    payload: ProfileUpdate,
):
    profile = await profile_service.get_profile_by_user_id(current_user.id)
    if not profile:
        return {"detail": "Profile not found"}

    await profile_service.update_profile(
        user_id=profile.user_id,
        displayed_name=payload.displayed_name,
        bio=payload.bio,
        social_links=payload.social_links,
    )
    return {"detail": "Profile updated successfully"}


@router.delete("/me")
async def delete_current_user_profile(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    profile = await profile_service.get_profile_by_user_id(current_user.id)
    if not profile:
        return {"detail": "Profile not found"}

    await profile_service.hard_delete_profile(user_id=profile.user_id)
    return {"detail": "Profile deleted successfully"}


@router.post("/")
async def create_profile(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    payload: ProfileCreate,
):
    await profile_service.create_profile(
        user_id=current_user.id,
        displayed_name=payload.displayed_name,
        bio=payload.bio,
        social_links=payload.social_links,
    )
    return {"detail": "Profile created successfully"}


@router.get("/search", response_model=list[ProfileRead])
async def search_profiles(
    query: str,
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    profiles = await profile_service.full_text_search_profiles(query)
    return [
        ProfileRead.model_validate(profile, from_attributes=True)
        for profile in profiles
    ]


@router.get("/")
async def get_all_profiles(
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    profiles = await profile_service.get_all_profiles()
    return [
        ProfileRead.model_validate(profile, from_attributes=True)
        for profile in profiles
    ]
