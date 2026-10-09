import logging
import os
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from yn.modules.discovery.indexer import IndexResult, SessionFactory, TrackIndexer
from yn.shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


def _save_cursor(cursor_path: Path, track_id: UUID) -> None:
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=cursor_path.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
        try:
            temporary.write(str(track_id))
            temporary.flush()
            os.fsync(temporary.fileno())
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise
    try:
        temporary_path.replace(cursor_path)
    finally:
        temporary_path.unlink(missing_ok=True)


async def backfill(
    session_factory: SessionFactory,
    indexer: TrackIndexer,
    cursor_path: Path,
    *,
    page_size: int = 100,
    dry_run: bool = False,
    restart: bool = False,
) -> Counter[IndexResult]:
    """Index existing tracks and resume only after a fully successful page."""
    if not 1 <= page_size <= 1000:
        raise ValueError("Page size must be between 1 and 1000")

    after: UUID | None = None
    if restart:
        if not dry_run:
            cursor_path.unlink(missing_ok=True)
    elif cursor_path.exists():
        after = UUID(cursor_path.read_text(encoding="utf-8").strip())

    counts: Counter[IndexResult] = Counter()
    while True:
        async with session_factory() as session:
            async with UnitOfWork(session) as uow:
                track_ids = await uow.track_embeddings.get_track_ids(
                    after=after, limit=page_size
                )
        if not track_ids:
            return counts

        for track_id in track_ids:
            result = await indexer.index_track(track_id, dry_run=dry_run)
            if result == "stale":
                raise RuntimeError(
                    f"Track {track_id} changed during indexing; rerun to resume this page"
                )
            counts[result] += 1

        after = track_ids[-1]
        if not dry_run:
            _save_cursor(cursor_path, after)
        logger.info("Processed page ending at %s: %s", after, dict(counts))
