from yn.shared.errors import AppError


class CommentaryNotFoundError(AppError):
    status_code = 404
    code = "commentary_not_found"
    detail = "Commentary not found"


class CommentaryParentNotFoundError(AppError):
    status_code = 404
    code = "commentary_parent_not_found"
    detail = "Parent commentary not found"


class CommentaryParentPostMismatchError(AppError):
    status_code = 400
    code = "commentary_parent_post_mismatch"
    detail = "Parent commentary belongs to another post"
