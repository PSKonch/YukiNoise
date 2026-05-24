from yn.shared.errors import AppError


class ArtistConflictError(AppError):
    status_code = 409
    code = "artist_conflict"
    detail = "Artist data conflicts with existing records"


class ArtistAlreadyExistsError(AppError):
    status_code = 409
    code = "artist_already_exists"
    detail = "Artist already exists for this user"


class ArtistDisplayedNameTakenError(AppError):
    status_code = 409
    code = "artist_displayed_name_taken"
    detail = "Displayed name is already taken"


class ArtistNotFoundError(AppError):
    status_code = 404
    code = "artist_not_found"
    detail = "Artist not found"


class EmptyArtistUpdateError(AppError):
    status_code = 400
    code = "empty_artist_update"
    detail = "At least one field must be provided"
