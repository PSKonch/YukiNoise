import asyncio
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from yn.modules.auth.auth import oauth2_scheme
from yn.modules.auth.deps import get_security_manager
from yn.modules.auth.security import SecurityManager
from yn.modules.auth.service import AuthService
from yn.modules.discovery.embedding_provider import (
    E5HuggingFaceEmbeddingProvider,
    EmbeddingProvider,
)
from yn.modules.discovery.errors import (
    DiscoveryDisabledError,
    DiscoveryProviderUnavailableError,
)
from yn.modules.discovery.generation_provider import (
    CurationGenerator,
    GroqCurationGenerator,
)
from yn.modules.discovery.rate_limit import DiscoveryRateLimiter
from yn.modules.discovery.service import DiscoveryService
from yn.modules.users.dto import UserDTO
from yn.shared.cache.redis_cache import get_redis_cache
from yn.shared.database import async_primary_session
from yn.shared.settings import settings
from yn.shared.unit_of_work import UnitOfWork


def require_discovery_enabled() -> None:
    if not settings.discovery_enabled:
        raise DiscoveryDisabledError


@lru_cache
def get_embedding_provider() -> E5HuggingFaceEmbeddingProvider:
    return E5HuggingFaceEmbeddingProvider()


async def get_request_embedding_provider() -> EmbeddingProvider:
    try:
        return await asyncio.to_thread(get_embedding_provider)
    except Exception as exc:
        raise DiscoveryProviderUnavailableError from exc


@lru_cache
def get_curation_generator() -> GroqCurationGenerator:
    if not settings.llm_api_key or settings.llm_api_key == "your-llm-api-key":
        raise DiscoveryDisabledError("Set LLM_API_KEY to enable curation preview")
    return GroqCurationGenerator(
        settings.llm_api_key,
        settings.llm_generation_model,
        timeout_seconds=settings.discovery_provider_timeout_seconds,
    )


async def get_discovery_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    security: Annotated[SecurityManager, Depends(get_security_manager)],
) -> UserDTO:
    # Reuse the existing auth service, but close its transaction before inference.
    async with async_primary_session() as session:
        async with UnitOfWork(session) as uow:
            user = await AuthService(
                uow=uow, security=security
            ).get_user_from_access_token(token)
    await DiscoveryRateLimiter(get_redis_cache()).check(user.id)
    return user


def get_discovery_service(
    provider: Annotated[EmbeddingProvider, Depends(get_request_embedding_provider)],
) -> DiscoveryService:
    return DiscoveryService(async_primary_session, provider)


def get_curator_service(
    provider: Annotated[EmbeddingProvider, Depends(get_request_embedding_provider)],
    generator: Annotated[CurationGenerator, Depends(get_curation_generator)],
) -> DiscoveryService:
    return DiscoveryService(
        async_primary_session,
        provider,
        generator,
        retrieval_limit=settings.discovery_retrieval_limit,
    )
