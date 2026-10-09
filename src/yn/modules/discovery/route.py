import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends

from yn.modules.discovery.deps import (
    get_curator_service,
    get_discovery_service,
    get_discovery_user,
    require_discovery_enabled,
)
from yn.modules.discovery.errors import DiscoveryProviderUnavailableError
from yn.modules.discovery.schemas import (
    CurationPreviewRead,
    CurationPreviewRequest,
    DiscoverySearchRequest,
    SearchTrackRead,
)
from yn.modules.discovery.service import DiscoveryService
from yn.modules.users.dto import UserDTO
from yn.shared.settings import settings

router = APIRouter(
    prefix="/discovery",
    tags=["discovery"],
    dependencies=[Depends(require_discovery_enabled)],
)


@router.post("/search")
async def search_tracks(
    payload: DiscoverySearchRequest,
    current_user: Annotated[UserDTO, Depends(get_discovery_user)],
    service: Annotated[DiscoveryService, Depends(get_discovery_service)],
) -> list[SearchTrackRead]:
    try:
        async with asyncio.timeout(settings.discovery_request_timeout_seconds):
            tracks = await service.search(payload.query, limit=payload.limit)
    except TimeoutError as exc:
        raise DiscoveryProviderUnavailableError from exc
    return [SearchTrackRead.model_validate(track) for track in tracks]


@router.post("/curations/preview")
async def preview_curation(
    payload: CurationPreviewRequest,
    current_user: Annotated[UserDTO, Depends(get_discovery_user)],
    service: Annotated[DiscoveryService, Depends(get_curator_service)],
) -> CurationPreviewRead:
    try:
        async with asyncio.timeout(settings.discovery_request_timeout_seconds):
            result = await service.preview(payload.query, limit=payload.limit)
    except TimeoutError as exc:
        raise DiscoveryProviderUnavailableError from exc
    return CurationPreviewRead.model_validate(result.model_dump())
