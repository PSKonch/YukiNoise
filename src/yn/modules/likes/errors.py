from yn.shared.errors import AppError


class LikeAlreadyExistsError(AppError):
    status_code = 409
    code = "like_already_exists"
    detail = "Target is already liked"


class LikeNotFoundError(AppError):
    status_code = 404
    code = "like_not_found"
    detail = "Like not found"


class LikeTargetNotFoundError(AppError):
    status_code = 404
    code = "like_target_not_found"
    detail = "Like target not found"
