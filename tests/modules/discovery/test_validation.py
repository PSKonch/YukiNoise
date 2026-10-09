from dataclasses import replace
from uuid import uuid4

import pytest

from yn.modules.discovery.document_builder import DocumentBuilder, TrackIndexSource
from yn.modules.discovery.dto import TrackCandidateDTO
from yn.modules.discovery.schemas import GeneratedCuration, GeneratedTrack
from yn.modules.discovery.validation import available_sources, validate_curation


@pytest.fixture
def candidate() -> TrackCandidateDTO:
    track_id = uuid4()
    source = TrackIndexSource(
        track_id=str(track_id),
        track_title="Первый снег",
        genres=("ambient",),
        artist_name="Yuki",
        artist_bio=None,
        release_title="Winter",
        release_description=None,
    )
    document = DocumentBuilder(source).build()
    return TrackCandidateDTO(
        track_id=track_id,
        source=source,
        document_text=document.text,
        content_hash=document.content_hash,
        distance=0.1,
    )


def test_available_sources_lists_populated_fields(candidate: TrackCandidateDTO) -> None:
    assert available_sources(candidate) == [
        "track.title",
        "track.genres",
        "artist.displayed_name",
        "release.title",
    ]


def test_curator_can_cite_featured_artists(candidate: TrackCandidateDTO) -> None:
    candidate = replace(
        candidate, source=replace(candidate.source, featured_artist_names=("Guest",))
    )
    result = GeneratedCuration(
        title="Подборка",
        summary="",
        tracks=[
            GeneratedTrack(
                track_id=candidate.track_id,
                reason="Совместный трек с Guest.",
                sources=["track.featured_artists"],
            )
        ],
    )

    assert "track.featured_artists" in available_sources(candidate)
    assert validate_curation(result, [candidate], limit=8) == result


@pytest.mark.parametrize("empty_text", [None, "", " \t\n"])
def test_available_sources_omits_empty_fields(
    candidate: TrackCandidateDTO, empty_text: str | None
) -> None:
    candidate = replace(
        candidate,
        source=replace(
            candidate.source,
            track_title=" \t",
            genres=(" ", "\t", ""),
            artist_bio=empty_text,
            release_description=empty_text,
        ),
    )

    assert available_sources(candidate) == ["artist.displayed_name", "release.title"]


def test_validation_filters_ids_duplicates_and_sources_without_mutating_input(
    candidate: TrackCandidateDTO,
) -> None:
    valid = GeneratedTrack(
        track_id=candidate.track_id,
        reason="В жанрах указан ambient.",
        sources=["track.genres", "artist.bio", "track.genres", "track.title"],
    )
    unknown = valid.model_copy(update={"track_id": uuid4()})
    no_evidence = valid.model_copy(update={"sources": ["artist.bio"]})
    result = GeneratedCuration(
        title="Зимняя музыка",
        summary="Треки в жанре ambient.",
        tracks=[unknown, no_evidence, valid, valid],
    )
    original = result.model_dump()

    validated = validate_curation(result, [candidate], limit=8)

    assert validated.tracks == [
        valid.model_copy(update={"sources": ["track.genres", "track.title"]})
    ]
    assert validated.title == result.title
    assert validated.summary == result.summary
    assert result.model_dump() == original


@pytest.mark.parametrize("limit", [-1, 0, 1, 2, 20])
def test_validation_applies_limit_in_generated_order(
    candidate: TrackCandidateDTO, limit: int
) -> None:
    other_id = uuid4()
    other = replace(
        candidate,
        track_id=other_id,
        source=replace(candidate.source, track_id=str(other_id)),
    )
    result = GeneratedCuration(
        title="Подборка",
        summary="",
        tracks=[
            GeneratedTrack(
                track_id=track.track_id,
                reason="В жанрах указан ambient.",
                sources=["track.genres"],
            )
            for track in [other, candidate]
        ],
    )

    validated = validate_curation(result, [candidate, other], limit=limit)

    assert [track.track_id for track in validated.tracks] == [
        other_id,
        candidate.track_id,
    ][: max(limit, 0)]
    if limit <= 0:
        assert validated == GeneratedCuration.empty()


@pytest.mark.parametrize(
    "rejection", ["unknown_id", "missing_sources", "no_candidates"]
)
def test_validation_returns_empty_curation_when_every_track_is_rejected(
    candidate: TrackCandidateDTO, rejection: str
) -> None:
    track = GeneratedTrack(
        track_id=uuid4() if rejection == "unknown_id" else candidate.track_id,
        reason="В жанрах указан ambient.",
        sources=["artist.bio"] if rejection == "missing_sources" else ["track.genres"],
    )
    result = GeneratedCuration(
        title="Сгенерированное название",
        summary="Сгенерированное описание",
        tracks=[track],
    )

    validated = validate_curation(
        result, [] if rejection == "no_candidates" else [candidate], limit=8
    )

    assert validated == GeneratedCuration.empty()
