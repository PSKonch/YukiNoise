from uuid import UUID

from sqlalchemy.exc import IntegrityError

from yn.modules.profiles.dto import ProfileDTO
from yn.modules.profiles.errors import ProfileConflictError
from yn.shared.unit_of_work import UnitOfWork


class ProfileService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_all_profiles(self, *, limit: int, offset: int) -> list[ProfileDTO]:
        profiles = await self.uow.profiles.get_profiles(limit=limit, offset=offset)
        return [ProfileDTO.from_orm(profile) for profile in profiles]

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

    async def full_text_search_profiles(
        self,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> list[ProfileDTO]:
        profiles = await self.uow.profiles.full_text_search_profiles(
            query,
            limit=limit,
            offset=offset,
        )

        if not profiles:
            corrected_profiles = (
                await self.uow.profiles.trgm_search_profiles_by_displayed_name(
                    query, limit=1, offset=0
                )
            )
            if corrected_profiles:
                corrected_query = corrected_profiles[0].displayed_name
                if corrected_query != query:
                    profiles = await self.uow.profiles.full_text_search_profiles(
                        corrected_query,
                        limit=limit,
                        offset=offset,
                    )

        return [ProfileDTO.from_orm(profile) for profile in profiles]

    async def create_profile(
        self,
        user_id: UUID,
        displayed_name: str,
        bio: str | None = None,
        social_links: dict[str, str] | None = None,
    ) -> ProfileDTO:
        try:
            profile = await self.uow.profiles.create(
                user_id=user_id,
                displayed_name=displayed_name,
                bio=bio,
                social_links=social_links,
            )
        except IntegrityError as exc:
            raise ProfileConflictError from exc
        return ProfileDTO.from_orm(profile)

    async def update_profile(
        self,
        user_id: UUID,
        displayed_name: str | None = None,
        bio: str | None = None,
        social_links: dict[str, str] | None = None,
    ) -> bool:
        try:
            return await self.uow.profiles.update(
                user_id=user_id,
                displayed_name=displayed_name,
                bio=bio,
                social_links=social_links,
            )
        except IntegrityError as exc:
            raise ProfileConflictError from exc

    async def hard_delete_profile(self, user_id: UUID) -> bool:
        return await self.uow.profiles.hard_delete_profile(user_id)
