import asyncio
from math import isfinite
from typing import Protocol, Sequence

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

from yn.modules.discovery.errors import (
    DiscoveryInvalidModelOutputError,
    DiscoveryProviderUnavailableError,
)


class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def model_dimensions(self) -> int: ...

    async def embed_query(self, query: str) -> Sequence[float]: ...

    async def embed_documents(
        self, documents: Sequence[str]
    ) -> Sequence[Sequence[float]]: ...


def validate_vector(vector: list[float], expected_dimensions: int) -> list[float]:
    if len(vector) != expected_dimensions:
        raise DiscoveryInvalidModelOutputError(
            detail=f"Vector has {len(vector)} dimensions, expected {expected_dimensions}"
        )

    if not all(isfinite(x) for x in vector) or not any(vector):
        raise DiscoveryInvalidModelOutputError(
            detail="Vector contains non-finite values"
        )
    return vector


class E5HuggingFaceEmbeddingProvider:
    MODEL_ID = "intfloat/multilingual-e5-base"

    model_name = f"{MODEL_ID}:prefix-v1:normalized"
    model_dimensions = 768

    def __init__(self, client: Embeddings | None = None) -> None:
        if client is None:
            client = HuggingFaceEmbeddings(
                model_name=self.MODEL_ID,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        self._client = client
        self._lock = asyncio.Lock()

    async def embed_query(self, query: str) -> Sequence[float]:
        try:
            async with self._lock:
                vector = await self._client.aembed_query(f"query: {query}")
        except Exception as e:
            raise DiscoveryProviderUnavailableError(
                detail=f"Failed to embed query: {e}"
            ) from e
        return validate_vector(vector, self.model_dimensions)

    async def embed_documents(
        self, documents: Sequence[str]
    ) -> Sequence[Sequence[float]]:
        if not documents:
            return []

        try:
            async with self._lock:
                vectors = await self._client.aembed_documents(
                    [f"passage: {doc}" for doc in documents]
                )
        except Exception as e:
            raise DiscoveryProviderUnavailableError(
                detail=f"Failed to embed documents: {e}"
            ) from e
        if len(vectors) != len(documents):
            raise DiscoveryInvalidModelOutputError(
                detail=f"Expected {len(documents)} vectors, got {len(vectors)}"
            )
        return [validate_vector(vector, self.model_dimensions) for vector in vectors]
