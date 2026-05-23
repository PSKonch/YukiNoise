from yn.shared.errors import AppError


class ReleaseConflictError(AppError):
    status_code = 409
    code = "release_conflict"
    detail = "Release data conflicts with existing records"


class ReleaseNotFoundError(AppError):
    status_code = 404
    code = "release_not_found"
    detail = "Release not found"


class ReleaseAccessDeniedError(AppError):
    status_code = 403
    code = "release_access_denied"
    detail = "You do not have access to this release"


class ReleaseCoverUploadFailedError(AppError):
    status_code = 500
    code = "release_cover_upload_failed"
    detail = "Release cover upload failed"


class ReleaseNotDraftError(AppError):
    status_code = 409
    code = "release_not_draft"
    detail = "Release must be in draft status to upload tracks"


class ReleaseNotScheduledError(AppError):
    status_code = 409
    code = "release_not_scheduled"
    detail = "Release must be in scheduled status to cancel the release"
