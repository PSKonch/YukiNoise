from yn.shared.errors import AppError


class ProfileConflictError(AppError):
    status_code = 409
    code = "profile_conflict"
    detail = "Profile data conflicts with existing records"


class ProfileNotFoundError(AppError):
    status_code = 404
    code = "profile_not_found"
    detail = "Profile not found"


class EmptyProfileUpdateError(AppError):
    status_code = 400
    code = "empty_profile_update"
    detail = "At least one field must be provided"
