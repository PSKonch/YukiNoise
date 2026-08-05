from yn.shared.errors import AppError


class FollowAlreadyExistsError(AppError):
    status_code = 409
    code = "follow_already_exists"
    detail = "Artist is already followed"


class FollowNotFoundError(AppError):
    status_code = 404
    code = "follow_not_found"
    detail = "Follow not found"


class SelfFollowError(AppError):
    status_code = 400
    code = "self_follow_not_allowed"
    detail = "An artist cannot follow themselves"
