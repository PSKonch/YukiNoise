import asyncio
import json
from collections.abc import Sequence
from typing import Protocol

from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import SecretStr, ValidationError

from yn.modules.discovery.dto import TrackCandidateDTO
from yn.modules.discovery.errors import (
    DiscoveryInvalidModelOutputError,
)
from yn.modules.discovery.prompts import CURATOR_INPUT, CURATOR_INSTRUCTIONS
from yn.modules.discovery.schemas import GeneratedCuration
from yn.modules.discovery.validation import available_sources


class CurationGenerator(Protocol):
    async def generate(
        self,
        *,
        query: str,
        candidates: Sequence[TrackCandidateDTO],
        limit: int,
    ) -> GeneratedCuration: ...


class GroqCurationGenerator:
    def __init__(
        self, api_key: str, model_name: str, *, timeout_seconds: float
    ) -> None:
        model = ChatGroq(
            model_name=model_name,
            api_key=SecretStr(api_key),
            temperature=0.0,
            timeout=timeout_seconds,
            max_retries=1,
            max_tokens=2500,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CURATOR_INSTRUCTIONS),
                ("human", CURATOR_INPUT),
            ]
        ).partial(json_schema=json.dumps(GeneratedCuration.model_json_schema()))

        self._chain = prompt | model.with_structured_output(
            schema=GeneratedCuration, method="json_mode"
        )
        self._semaphore = asyncio.Semaphore(2)

    async def generate(
        self,
        *,
        query: str,
        candidates: Sequence[TrackCandidateDTO],
        limit: int,
    ) -> GeneratedCuration:
        context = json.dumps(
            [
                {
                    "track_id": str(c.track_id),
                    "document_text": c.document_text,
                    "available_sources": available_sources(c),
                }
                for c in candidates
            ],
            ensure_ascii=False,
        )

        try:
            async with self._semaphore:
                result = await self._chain.ainvoke(
                    {"query": query, "context": context, "limit": limit}
                )
        except (OutputParserException, ValidationError) as e:
            raise DiscoveryInvalidModelOutputError(
                detail=f"Failed to parse model output: {e}"
            ) from e

        if not isinstance(result, GeneratedCuration):
            raise DiscoveryInvalidModelOutputError(
                detail="The model returned an unexpected response type"
            )
        return result
