from yn.shared.errors import AppError


class PostConflictError(AppError):
    status_code = 409
    code = "post_conflict"
    detail = "Post data conflicts with existing records"


class PostNotFoundError(AppError):
    status_code = 404
    code = "post_not_found"
    detail = "Post not found"


class EmptyPostUpdateError(AppError):
    status_code = 400
    code = "empty_post_update"
    detail = "At least one field must be provided"
