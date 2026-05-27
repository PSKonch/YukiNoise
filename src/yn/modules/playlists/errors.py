from yn.shared.errors import AppError


class PlaylistConflictError(AppError):
    status_code = 409
    code = "playlist_conflict"
    detail = "Playlist data conflicts with existing records"


class PlaylistNotFoundError(AppError):
    status_code = 404
    code = "playlist_not_found"
    detail = "Playlist not found"


class PlaylistAccessDeniedError(AppError):
    status_code = 403
    code = "playlist_access_denied"
    detail = "You do not have access to this playlist"


class PlaylistTrackNotFoundError(AppError):
    status_code = 404
    code = "playlist_track_not_found"
    detail = "Track not found in playlist"


class EmptyPlaylistUpdateError(AppError):
    status_code = 400
    code = "empty_playlist_update"
    detail = "At least one field must be provided"
