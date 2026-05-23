from yn.shared.errors import AppError


class TrackUploadFailedError(AppError):
    status_code = 500
    code = "track_upload_failed"
    detail = "Track upload failed"


class TrackConflictError(AppError):
    status_code = 409
    code = "track_conflict"
    detail = "A track with this title already exists in the album"


class TrackFormatError(AppError):
    status_code = 415
    code = "track_format_not_supported"
    detail = "Only WAV and MP3 files are supported"


class TrackMetadataError(AppError):
    status_code = 400
    code = "track_metadata_error"
    detail = "Could not read audio metadata"


class TrackNotFoundError(AppError):
    status_code = 404
    code = "track_not_found"
    detail = "Track not found"
