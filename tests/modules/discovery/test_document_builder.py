from collections.abc import Callable
from dataclasses import replace

import pytest

from yn.modules.discovery.document_builder import DocumentBuilder, TrackIndexSource


@pytest.fixture
def source() -> TrackIndexSource:
    return TrackIndexSource(
        track_id="track-1",
        track_title="Первый снег",
        genres=("ambient", "electronic"),
        artist_name="Yuki",
        artist_bio="Музыка о зиме",
        release_title="Winter",
        release_description="Звуки ночного города",
    )


def test_builds_readable_document(source: TrackIndexSource) -> None:
    document = DocumentBuilder(source).build()

    assert document.source_id == "track-1"
    assert document.schema_version == 1
    assert len(document.content_hash) == 64
    assert document.text == (
        "Track title: Первый снег\n"
        "Genres: ambient, electronic\n"
        "Artist name: Yuki\n"
        "Artist bio: Музыка о зиме\n"
        "Release title: Winter\n"
        "Release description: Звуки ночного города"
    )


def test_formatting_noise_does_not_change_document(source: TrackIndexSource) -> None:
    noisy_source = replace(
        source,
        track_title="  Первый\tснег\n",
        genres=(" electronic ", "ambient", "", "  ", "ambient"),
        artist_name=" Yuki\t",
        artist_bio="\nМузыка   о\tзиме ",
        release_title=" Winter ",
        release_description="Звуки\u00a0ночного\nгорода",
    )

    assert DocumentBuilder(noisy_source).build() == DocumentBuilder(source).build()


@pytest.mark.parametrize("empty_text", [None, "", " \t\n"])
def test_omits_empty_optional_fields_and_genres(
    source: TrackIndexSource, empty_text: str | None
) -> None:
    minimal_source = replace(
        source,
        genres=("", " \t"),
        artist_bio=empty_text,
        release_description=empty_text,
    )
    document = DocumentBuilder(minimal_source).build()
    baseline = DocumentBuilder(
        replace(source, genres=(), artist_bio=None, release_description=None)
    ).build()

    assert document == baseline
    assert document.text == (
        "Track title: Первый снег\nArtist name: Yuki\nRelease title: Winter"
    )


@pytest.mark.parametrize(
    "make_change",
    [
        lambda source: replace(source, track_title="Другой трек"),
        lambda source: replace(source, genres=("jazz",)),
        lambda source: replace(source, artist_name="Другой артист"),
        lambda source: replace(source, artist_bio="Другая биография"),
        lambda source: replace(source, release_title="Другой релиз"),
        lambda source: replace(source, release_description="Другое описание"),
    ],
    ids=[
        "track_title",
        "genres",
        "artist_name",
        "artist_bio",
        "release_title",
        "release_description",
    ],
)
def test_content_changes_update_hash(
    source: TrackIndexSource,
    make_change: Callable[[TrackIndexSource], TrackIndexSource],
) -> None:
    original = DocumentBuilder(source).build()
    updated = DocumentBuilder(make_change(source)).build()

    assert updated.text != original.text
    assert updated.content_hash != original.content_hash


def test_track_id_does_not_affect_text_or_hash(source: TrackIndexSource) -> None:
    original = DocumentBuilder(source).build()
    updated = DocumentBuilder(replace(source, track_id="track-2")).build()

    assert updated.source_id == "track-2"
    assert updated.text == original.text
    assert updated.content_hash == original.content_hash


def test_schema_version_changes_hash(source: TrackIndexSource) -> None:
    class NextVersionBuilder(DocumentBuilder):
        SCHEMA_VERSION = 2

    original = DocumentBuilder(source).build()
    updated = NextVersionBuilder(source).build()

    assert updated.schema_version == 2
    assert updated.text == original.text
    assert updated.content_hash != original.content_hash
