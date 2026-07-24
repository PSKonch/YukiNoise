from yn.shared.errors import AppError


class EmailAlreadyTakenError(AppError):
    status_code = 409
    code = "email_already_taken"
    detail = "Email already registered"
