from uuid import UUID

from yn.modules.artists.errors import ArtistNotFoundError
from yn.modules.tracks.errors import InvalidTrackFeaturesError
from yn.shared.unit_of_work import UnitOfWork


async def validate_featured_artists(
    uow: UnitOfWork, *, artist_id: UUID, featured_artist_ids: list[UUID]
) -> None:
    if artist_id in featured_artist_ids or len(featured_artist_ids) != len(
        set(featured_artist_ids)
    ):
        raise InvalidTrackFeaturesError
    if not featured_artist_ids:
        return

    artists = await uow.artists.get_artists_by_ids(featured_artist_ids)
    if len(artists) != len(featured_artist_ids):
        raise ArtistNotFoundError
