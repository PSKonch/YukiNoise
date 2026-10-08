from collections.abc import Sequence
from uuid import UUID

from yn.modules.discovery.dto import TrackCandidateDTO
from yn.modules.discovery.schemas import GeneratedCuration, GeneratedTrack, SourceField


def available_sources(candidate: TrackCandidateDTO) -> list[SourceField]:
    """Return populated source fields that the generated answer may cite."""
    source = candidate.source
    values: list[tuple[SourceField, str | None]] = [
        ("track.title", source.track_title),
        (
            "track.genres",
            ", ".join(genre.strip() for genre in source.genres if genre.strip()),
        ),
        ("artist.displayed_name", source.artist_name),
        ("artist.bio", source.artist_bio),
        ("release.title", source.release_title),
        ("release.description", source.release_description),
    ]
    return [name for name, value in values if value and value.strip()]


def validate_curation(
    result: GeneratedCuration,
    candidates: Sequence[TrackCandidateDTO],
    *,
    limit: int,
) -> GeneratedCuration:
    """Keep unique candidate IDs with references to populated source fields."""
    if limit <= 0:
        return GeneratedCuration.empty()

    allowed = {candidate.track_id: candidate for candidate in candidates}
    seen: set[UUID] = set()
    tracks: list[GeneratedTrack] = []
    for track in result.tracks:
        if track.track_id not in allowed or track.track_id in seen:
            continue

        sources = [
            field
            for field in dict.fromkeys(track.sources)
            if field in available_sources(allowed[track.track_id])
        ]
        if not sources:
            continue

        seen.add(track.track_id)
        tracks.append(track.model_copy(update={"sources": sources}))
        if len(tracks) == limit:
            break

    if not tracks:
        return GeneratedCuration.empty()
    return result.model_copy(update={"tracks": tracks})
