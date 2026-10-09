from functools import lru_cache

from yn.modules.discovery.embedding_provider import E5HuggingFaceEmbeddingProvider


@lru_cache
def get_embedding_provider() -> E5HuggingFaceEmbeddingProvider:
    return E5HuggingFaceEmbeddingProvider()
