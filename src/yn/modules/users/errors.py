from yn.shared.errors import AppError


class EmailAlreadyTakenError(AppError):
    status_code = 409
    code = "email_already_taken"
    detail = "Email already registered"


class InvalidLoginCredentialsError(AppError):
    status_code = 401
    code = "invalid_login_credentials"
    detail = "Incorrect username or password"
    headers = {"WWW-Authenticate": "Bearer"}


class InvalidAuthCredentialsError(AppError):
    status_code = 401
    code = "invalid_auth_credentials"
    detail = "Could not validate credentials"
    headers = {"WWW-Authenticate": "Bearer"}
