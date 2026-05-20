from yn.shared.errors import AppError


class AlbumNotFoundError(AppError):
    status_code = 404
    code = "album_not_found"
    detail = "Album not found"


class AlbumAccessDeniedError(AppError):
    status_code = 403
    code = "album_access_denied"
    detail = "You do not have access to this album"


class TrackUploadFailedError(AppError):
    status_code = 500
    code = "track_upload_failed"
    detail = "Track upload failed"


class TrackMetadataError(AppError):
    status_code = 400
    code = "track_metadata_error"
    detail = "Could not read audio metadata"
