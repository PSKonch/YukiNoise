from yn.shared.errors import AppError


class PlaybackNotFoundError(AppError):
    status_code = 404
    code = "playback_not_found"
    detail = "Playback not found"


class PlaybackContextNotFoundError(AppError):
    status_code = 404
    code = "playback_context_not_found"
    detail = "Playback context was not found or is not available"


class PlaybackConflictError(AppError):
    status_code = 409
    code = "playback_conflict"
    detail = "Playback state changed; refresh it and retry"


class PlaybackDeviceConflictError(AppError):
    status_code = 409
    code = "playback_device_conflict"
    detail = "Another device controls playback"


class PlaybackProgressRejectedError(AppError):
    status_code = 409
    code = "playback_progress_rejected"
    detail = "Playback progress was rejected"
