from uuid import UUID

from yn.modules.profiles.dto import ProfileDTO
from yn.shared.unit_of_work import UnitOfWork


class ProfileService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_profile_by_user_id(self, user_id: UUID) -> ProfileDTO | None:
        profile = await self.uow.profiles.get_profile_by_user_id(user_id)
        return ProfileDTO.from_orm(profile) if profile else None

    async def get_profile_by_id(self, profile_id: UUID) -> ProfileDTO | None:
        profile = await self.uow.profiles.get_profile_by_id(profile_id)
        return ProfileDTO.from_orm(profile) if profile else None

    async def get_profile_by_displayed_name(
        self, displayed_name: str
    ) -> ProfileDTO | None:
        profile = await self.uow.profiles.get_profile_by_displayed_name(displayed_name)
        return ProfileDTO.from_orm(profile) if profile else None

    async def full_text_search_profiles(self, query: str) -> list[ProfileDTO]:
        profiles = await self.uow.profiles.full_text_search_profiles(query)
        return [ProfileDTO.from_orm(profile) for profile in profiles]

    async def create_profile(
        self,
        user_id: UUID,
        displayed_name: str,
        bio: str | None = None,
        social_links: dict[str, str] | None = None,
    ) -> ProfileDTO:
        profile = await self.uow.profiles.create(
            user_id=str(user_id),
            displayed_name=displayed_name,
            bio=bio,
            social_links=social_links,
        )
        return ProfileDTO.from_orm(profile)
