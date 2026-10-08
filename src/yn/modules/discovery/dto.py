from dataclasses import dataclass
from uuid import UUID

from yn.modules.discovery.document_builder import TrackIndexSource


@dataclass(frozen=True, slots=True)
class TrackCandidateDTO:
    track_id: UUID
    source: TrackIndexSource
    document_text: str
    content_hash: str
    distance: float


@dataclass(frozen=True, slots=True)
class SearchTrackDTO:
    track_id: UUID
    track_title: str
    artist_name: str
    release_title: str
    distance: float

    @classmethod
    def from_candidate(cls, candidate: TrackCandidateDTO) -> "SearchTrackDTO":
        return cls(
            track_id=candidate.track_id,
            track_title=candidate.source.track_title,
            artist_name=candidate.source.artist_name,
            release_title=candidate.source.release_title,
            distance=candidate.distance,
        )
