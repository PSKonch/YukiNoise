from yn.shared.errors import AppError


class PlaybackNotFoundError(AppError):
    status_code = 404
    code = "playback_not_found"
    detail = "Playback not found"


class TrackNotFoundError(AppError):
    status_code = 404
    code = "playback_track_not_found"
    detail = "Track not found"
