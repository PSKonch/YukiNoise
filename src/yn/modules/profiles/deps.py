from typing import Annotated

from fastapi import Depends

from yn.modules.profiles.service import ProfileService
from yn.shared.unit_of_work import UnitOfWork, get_uow


def get_profile_service(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> ProfileService:
    return ProfileService(uow)
