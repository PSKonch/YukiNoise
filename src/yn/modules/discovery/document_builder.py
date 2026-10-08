from dataclasses import dataclass, fields
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class TrackIndexSource:
    track_id: str
    track_title: str
    genres: tuple[str, ...]
    artist_name: str
    artist_bio: str | None
    release_title: str
    release_description: str | None


@dataclass(frozen=True, slots=True)
class TrackEmbeddingDocument:
    source_id: str
    text: str
    content_hash: str
    schema_version: int


class DocumentBuilder:
    SCHEMA_VERSION: int = 1

    def __init__(
        self,
        source: TrackIndexSource,
    ) -> None:
        self.source = source

    def build(self) -> TrackEmbeddingDocument:
        text = "\n".join(self._clean_source())
        hash_input = f"{self.SCHEMA_VERSION}\n{text}"

        return TrackEmbeddingDocument(
            source_id=self.source.track_id,
            text=text,
            content_hash=sha256(hash_input.encode("utf-8")).hexdigest(),
            schema_version=self.SCHEMA_VERSION,
        )

    def _clean_source(self) -> list[str]:
        labels = {
            "track_title": "Track title",
            "genres": "Genres",
            "artist_name": "Artist name",
            "artist_bio": "Artist bio",
            "release_title": "Release title",
            "release_description": "Release description",
        }
        res: list[str] = []
        for field in fields(self.source):
            if field.name not in labels:
                continue

            value = getattr(self.source, field.name)

            if isinstance(value, str):
                cleaned_value = " ".join(value.split())
            elif isinstance(value, tuple):
                items = {" ".join(item.split()) for item in value}
                cleaned_value = ", ".join(sorted(items - {""}))
            else:
                continue

            if cleaned_value:
                res.append(f"{labels[field.name]}: {cleaned_value}")

        return res
