import argparse
import asyncio
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from yn.modules.discovery.backfill import backfill
from yn.modules.discovery.deps import get_embedding_provider
from yn.modules.discovery.embedding_provider import (
    E5HuggingFaceEmbeddingProvider,
    EmbeddingProvider,
)
from yn.modules.discovery.indexer import TrackIndexer
from yn.shared.database import async_primary_engine, async_primary_session


class DryRunEmbeddingProvider:
    """Expose index metadata without loading model weights for a dry run."""

    model_name = E5HuggingFaceEmbeddingProvider.model_name
    model_dimensions = E5HuggingFaceEmbeddingProvider.model_dimensions

    async def embed_query(self, query: str) -> list[float]:
        raise RuntimeError("Dry run must not calculate embeddings")

    async def embed_documents(self, documents: Sequence[str]) -> list[list[float]]:
        raise RuntimeError("Dry run must not calculate embeddings")


async def run(args: argparse.Namespace) -> None:
    async_primary_engine.echo = False
    provider: EmbeddingProvider
    if args.dry_run:
        provider = DryRunEmbeddingProvider()
    else:
        provider = await asyncio.to_thread(get_embedding_provider)
    try:
        counts = await backfill(
            async_primary_session,
            TrackIndexer(async_primary_session, provider),
            args.cursor_file,
            page_size=args.page_size,
            dry_run=args.dry_run,
            restart=args.restart,
        )
        print(json.dumps(counts, ensure_ascii=False))
    finally:
        await async_primary_engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build or resume the track search index"
    )
    parser.add_argument(
        "--cursor-file", type=Path, default=Path(".discovery-backfill.cursor")
    )
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--restart", action="store_true", help="Start a new full scan")
    args = parser.parse_args()
    if not 1 <= args.page_size <= 1000:
        parser.error("--page-size must be between 1 and 1000")
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
