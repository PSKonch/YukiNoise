from yn.shared.errors import AppError


class AlbumConflictError(AppError):
    status_code = 409
    code = "album_conflict"
    detail = "Album data conflicts with existing records"


class AlbumNotFoundError(AppError):
    status_code = 404
    code = "album_not_found"
    detail = "Album not found"


class AlbumAccessDeniedError(AppError):
    status_code = 403
    code = "album_access_denied"
    detail = "You do not have access to this album"
