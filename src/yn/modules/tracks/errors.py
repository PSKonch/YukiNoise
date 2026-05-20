from yn.shared.errors import AppError


class TrackUploadFailedError(AppError):
    status_code = 500
    code = "track_upload_failed"
    detail = "Track upload failed"


class TrackMetadataError(AppError):
    status_code = 400
    code = "track_metadata_error"
    detail = "Could not read audio metadata"
